import numpy as np
import random
import json
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import os
import glob

# Import các helper cục bộ
try:
    from src.nltk_utils import bag_of_words, tokenize, stem
    from src.model import NeuralNet
    from src.database import SessionLocal, engine, Base
    from src.crud import sync_bot_response
except ModuleNotFoundError:
    from nltk_utils import bag_of_words, tokenize, stem
    from model import NeuralNet
    from database import SessionLocal, engine, Base
    from crud import sync_bot_response

# Từ dừng tiếng Việt cần loại bỏ khi tạo từ điển để giảm nhiễu NLP
ignore_words = [
    '?', '.', '!', ',', '-', '_', '/', ':', ';',
    'tôi', 'bị', 'thì', 'là', 'và', 'ạ', 'nhé', 'nha', 'với', 'cho', 'của', 'ở', 'tại'
]

# Hàm huấn luyện mô hình PyTorch tái sử dụng
def train_model(X_train, y_train, input_size, output_size, category_name="Model", num_epochs=1000, batch_size=8, learning_rate=0.001, hidden_size=16):
    class ChatDataset(Dataset):
        def __init__(self):
            self.n_samples = len(X_train)
            self.x_data = X_train
            self.y_data = y_train

        def __getitem__(self, index):
            return self.x_data[index], self.y_data[index]

        def __len__(self):
            return self.n_samples

    dataset = ChatDataset()
    train_loader = DataLoader(dataset=dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Khởi tạo mạng nơ-ron
    model = NeuralNet(input_size, hidden_size, output_size).to(device)
    model.train() # Đặt mô hình ở chế độ huấn luyện (kích hoạt Dropout)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    print(f"\n--- Training {category_name} (vocab: {input_size}, classes: {output_size}) ---")
    for epoch in range(num_epochs):
        for (words, labels) in train_loader:
            words = words.to(device)
            labels = labels.to(dtype=torch.long).to(device)

            # Forward pass
            outputs = model(words)
            loss = criterion(outputs, labels)

            # Backward and optimize
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        if (epoch + 1) % 200 == 0:
            print(f'Epoch [{epoch + 1}/{num_epochs}], Loss: {loss.item():.4f}')

    print(f'Training {category_name} complete. Final loss: {loss.item():.4f}')
    return model.state_dict()


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    intents_dir = os.path.join(script_dir, "..", "data", "intents")

    # 1. Tìm tất cả các file JSON chủ đề kịch bản
    intents_files = glob.glob(os.path.join(intents_dir, "*.json"))
    if not intents_files:
        # Nếu data/intents rỗng, kiểm tra file intents.json ở gốc làm dự phòng
        fallback_paths = [
            os.path.join(script_dir, '..', 'intents.json'),
            os.path.join(script_dir, 'intents.json'),
            'intents.json'
        ]
        for path in fallback_paths:
            if os.path.exists(path):
                intents_files = [path]
                break

    if not intents_files:
        raise ValueError("No intents data files found. Please run migrate_intents.py first!")

    # 2. Khởi tạo database session để đồng bộ câu trả lời xuống MySQL
    try:
        Base.metadata.create_all(bind=engine)
        print("Successfully ensured database tables are created.")
    except Exception as e:
        print(f"WARNING: Database connection failed. Syncing responses to DB will be skipped. Error: {e}")

    db = SessionLocal()

    # 3. Đọc dữ liệu từ các file kịch bản
    # Cấu trúc: data_by_category[category_name] = intents_list
    data_by_category = {}
    
    for file_path in intents_files:
        # Tên file không có phần mở rộng chính là tên Chủ đề (Category)
        category = os.path.splitext(os.path.basename(file_path))[0]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                intents_list = content.get("intents", [])
                if intents_list:
                    data_by_category[category] = intents_list
                    print(f"Read category '{category}' with {len(intents_list)} intents from {os.path.basename(file_path)}")
                    
                    # Đồng bộ câu trả lời (responses) xuống Database MySQL/SQLite (Phương pháp 2)
                    for intent in intents_list:
                        tag = intent.get("tag")
                        responses = intent.get("responses", [])
                        if tag and responses:
                            try:
                                sync_bot_response(db, tag=tag, category=category, responses=responses)
                            except Exception as db_err:
                                print(f"WARNING: Could not sync responses for tag '{tag}' to DB. Error: {db_err}")
        except Exception as e:
            print(f"ERROR: Failed to process intents file {file_path}. Error: {e}")

    db.close()
    print("Completed syncing all responses to Database.")

    # 4. HUẤN LUYỆN MÔ HÌNH ĐỊNH TUYẾN (ROUTER MODEL)
    # Router sẽ nhận câu hỏi và dự đoán Category (general, sales, health...)
    router_xy = []
    router_all_words = []
    router_categories = sorted(list(data_by_category.keys()))

    for category, intents_list in data_by_category.items():
        for intent in intents_list:
            for pattern in intent.get("patterns", []):
                w = tokenize(pattern)
                router_all_words.extend(w)
                router_xy.append((w, category))

    # Xử lý từ dừng & chuẩn hóa cho Router
    router_all_words = [stem(w) for w in router_all_words if w.lower() not in ignore_words]
    router_all_words = sorted(set(router_all_words))

    X_router = []
    y_router = []
    for (pattern_sentence, category) in router_xy:
        bag = bag_of_words(pattern_sentence, router_all_words)
        X_router.append(bag)
        label = router_categories.index(category)
        y_router.append(label)

    X_router = np.array(X_router)
    y_router = np.array(y_router)

    # Huấn luyện Router Model
    router_input_size = len(router_all_words)
    router_output_size = len(router_categories)
    
    router_state = train_model(
        X_train=X_router,
        y_train=y_router,
        input_size=router_input_size,
        output_size=router_output_size,
        category_name="Router (Classifier)",
        num_epochs=1000,
        hidden_size=16
    )

    # Lưu trọng số Router Model
    router_data = {
        "model_state": router_state,
        "input_size": router_input_size,
        "hidden_size": 16,
        "output_size": router_output_size,
        "all_words": router_all_words,
        "categories": router_categories
    }
    router_file = os.path.join(script_dir, "..", "data_router.pth")
    torch.save(router_data, router_file)
    print(f"Router Model saved to {router_file}")


    # 5. HUẤN LUYỆN CÁC MÔ HÌNH CHUYÊN SÂU (SPECIALIZED MODELS)
    # Với mỗi Category, ta huấn luyện 1 mô hình độc lập để phân loại Tag trong Category đó
    for category, intents_list in data_by_category.items():
        cat_xy = []
        cat_all_words = []
        cat_tags = []

        for intent in intents_list:
            tag = intent.get("tag")
            cat_tags.append(tag)
            for pattern in intent.get("patterns", []):
                w = tokenize(pattern)
                cat_all_words.extend(w)
                cat_xy.append((w, tag))

        cat_all_words = [stem(w) for w in cat_all_words if w.lower() not in ignore_words]
        cat_all_words = sorted(set(cat_all_words))
        cat_tags = sorted(set(cat_tags))

        X_cat = []
        y_cat = []
        for (pattern_sentence, tag) in cat_xy:
            bag = bag_of_words(pattern_sentence, cat_all_words)
            X_cat.append(bag)
            label = cat_tags.index(tag)
            y_cat.append(label)

        X_cat = np.array(X_cat)
        y_cat = np.array(y_cat)

        cat_input_size = len(cat_all_words)
        cat_output_size = len(cat_tags)

        # Huấn luyện mô hình chuyên biệt
        cat_state = train_model(
            X_train=X_cat,
            y_train=y_cat,
            input_size=cat_input_size,
            output_size=cat_output_size,
            category_name=f"Specialized Bot [{category}]",
            num_epochs=1000,
            hidden_size=16
        )

        # Lưu trọng số mô hình chuyên biệt
        cat_data = {
            "model_state": cat_state,
            "input_size": cat_input_size,
            "hidden_size": 16,
            "output_size": cat_output_size,
            "all_words": cat_all_words,
            "tags": cat_tags
        }
        cat_file = os.path.join(script_dir, "..", f"data_{category}.pth")
        torch.save(cat_data, cat_file)
        print(f"Specialized Bot [{category}] Model saved to {cat_file}")

    print("\n=======================================================")
    print("ALL MODELS HAVE BEEN TRAINED & SAVED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    main()

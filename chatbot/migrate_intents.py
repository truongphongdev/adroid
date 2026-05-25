import os
import json

def migrate():
    # 1. Định nghĩa phân nhóm các tag
    categories = {
        "general": ["greeting", "goodbye", "thanks", "funny", "weather", "capabilities", "identity"],
        "sales": ["items", "payments", "delivery", "consulting", "technical_support", "feedback", "careers", "location"],
        "health": ["health"]
    }

    # 2. Đọc file intents.json ở gốc làm nguồn
    source_path = "intents.json"
    if not os.path.exists(source_path):
        print(f"Error: {source_path} not found at root directory!")
        return

    with open(source_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 3. Tạo thư mục đích nếu chưa có
    target_dir = os.path.join("data", "intents")
    os.makedirs(target_dir, exist_ok=True)

    # 4. Phân loại các intent vào các nhóm chủ đề tương ứng
    categorized_data = {cat: {"intents": []} for cat in categories}
    
    for intent in data.get("intents", []):
        tag = intent.get("tag")
        matched = False
        for cat, tags in categories.items():
            if tag in tags:
                categorized_data[cat]["intents"].append(intent)
                matched = True
                break
        if not matched:
            # Nếu tag lạ chưa phân nhóm, mặc định cho vào general
            categorized_data["general"]["intents"].append(intent)
            print(f"WARNING: Tag '{tag}' is not categorized. Put into 'general' as fallback.")

    # 5. Lưu thành các file JSON tương ứng
    for cat, content in categorized_data.items():
        file_path = os.path.join(target_dir, f"{cat}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        print(f"Successfully migrated {len(content['intents'])} intents to {file_path}")

    # 6. Dọn dẹp tệp gộp tạm thời cũ trong data/intents nếu có
    old_merged_path = os.path.join(target_dir, "intents.json")
    if os.path.exists(old_merged_path):
        os.remove(old_merged_path)
        print(f"Removed old temporary merged file: {old_merged_path}")

    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()

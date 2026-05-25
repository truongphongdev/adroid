import nltk
from nltk.stem.porter import PorterStemmer
import numpy as np

# Tự động tải tài nguyên NLTK cần thiết nếu chưa có
for resource in ['tokenizers/punkt', 'tokenizers/punkt_tab']:
    try:
        nltk.data.find(resource)
    except LookupError:
        resource_name = resource.split('/')[-1]
        try:
            nltk.download(resource_name, quiet=True)
        except Exception:
            pass

stemmer = PorterStemmer()


import unicodedata

def tokenize(sentence):
    # Chuẩn hóa Unicode NFC để tránh khác biệt mã dấu tiếng Việt
    sentence = unicodedata.normalize('NFC', sentence)
    return nltk.word_tokenize(sentence)

def stem(word):
    return stemmer.stem(word.lower())

def bag_of_words(tokenized_sentence, words):
    # stem each word
    sentence_words = [stem(word) for word in tokenized_sentence]
    # initialize bag with 0 for each word
    bag = np.zeros(len(words), dtype=np.float32)
    for idx, w in enumerate(words):
        if w in sentence_words:
            bag[idx] = 1

    return bag











import os
import sys
import json
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

# -----------------------------
# 1) 경로 설정 (main.py와 동일한 원칙 적용)
# -----------------------------

def get_model_dir():
    """ 
    main.py에서 MODEL_ROOT_DIR이 결정되면, NER 모델은 그 하위 폴더에 있다고 가정합니다. 
    """
    # ★★★ 주의: 이 함수는 main.py의 MODEL_ROOT_DIR 정의 로직과 독립적으로 동작해야 합니다. ★★★
    
    # 1. 환경 변수 체크 (Electron에서 --model-dir이 전달되었다면, 그 경로를 따라가기 위한 기준)
    #    main.py가 전달하는 MODEL_ROOT_DIR을 알 수 없으므로, 최상위 경로를 재계산합니다.
    
    # (A) PyInstaller 환경 (배포 경로)
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
        # resources/backend_deploy/model/ner 경로를 생성
        return os.path.join(base_path, "model", "ner")
    
    # (B) 개발 환경 (하드코딩 경로)
    # main.py의 MODEL_ROOT_DIR이 C:\Users\...\model 이므로, NER 폴더를 추가합니다.
    real_model_path = r"C:\Syaptix\App\backend\model"
    if os.path.exists(real_model_path):
        return os.path.join(real_model_path, "ner")
        
    # (C) 소스코드 상대 경로 (최후의 폴백)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "model", "ner")


MODEL_DIR = get_model_dir()
MODEL_PATH = os.path.join(MODEL_DIR, "model.onnx")

# -----------------------------
# 2) 글로벌 변수 및 안전한 로드 (서버 크래시 방지)
# -----------------------------
tokenizer = None
id2label = {}
desired_tag_names = set()
session = None

# 파일 존재 시에만 모델 로드 시도 (서버가 크래시하지 않도록 Try-Except로 감쌈)
if os.path.exists(MODEL_DIR) and os.path.exists(os.path.join(MODEL_DIR, "config.json")):
    try:
        # 1. 토크나이저 및 라벨 로드
        tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
        
        with open(os.path.join(MODEL_DIR, "config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        id2label = {int(k): v for k, v in cfg.get("id2label", {}).items()}

        desired_tag_names = {id2label[i][2:] for i in [12, 13, 23, 37, 40, 55, 56, 66, 77, 80] if i in id2label}

        # 2. ONNX 세션 로드 (NPU/CPU Fallback 포함)
        if os.path.exists(MODEL_PATH):
            sess_options = ort.SessionOptions()
            sess_options.log_severity_level = 3
            try:
                session = ort.InferenceSession(
                    MODEL_PATH,
                    sess_options=sess_options,
                    providers=["QNNExecutionProvider", "CPUExecutionProvider"],
                    provider_options=[{"backend_path": "QnnHtp.dll", "profiling_level": "off"}, {}]
                )
            except Exception:
                session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
            # print("[NER] Model loaded successfully!") # (배포 시 로그 제거)
        
    except Exception as e:
        print(f"[NER Warning] Model loading failed at startup (files exist, but internal error): {e}") 
        tokenizer = None
        session = None
else:
    # 모델 파일이 디스크에 없을 경우
    print(f"[NER Info] Model files not found at {MODEL_DIR}. Waiting for download.")

# -----------------------------
# 3) 문장 처리 함수 정의
# -----------------------------
def extract_medical_terms(sentence: str):
    """
    주어진 문장에서 특정 태그에 해당하는 의학 용어를 추출합니다.
    """
    # 모델이 준비되지 않았으면 즉시 빈 리스트 반환 (안전장치)
    if not tokenizer or not session:
        return []

    try:
        enc = tokenizer(
            sentence,
            return_tensors="np",
            truncation=True,
            max_length=128,
            padding='max_length'
        )
        onnx_inputs = {}
        enc_np = {k: (v.astype(np.int64) if k in ['input_ids', 'attention_mask'] else v) for k, v in enc.items()}
        
        for inp in session.get_inputs():
            name = inp.name
            base = name.split(":")[0]
            if base in enc_np:
                onnx_inputs[name] = enc_np[base]

        outputs = session.run(None, onnx_inputs)
        logits = outputs[0]
        pred_ids = logits.argmax(-1)[0].tolist()
        labels_token = [id2label.get(i, "O") for i in pred_ids]

        tokens = tokenizer.tokenize(sentence)
        tagged_words = list(zip(tokens, labels_token[1:len(tokens)+1]))

        extracted_words_list = []
        current_entity_tokens = []
        current_tag_name = None

        for token, label in tagged_words:
            tag_name = label[2:] if label.startswith(('B-', 'I-')) else label
            
            if tag_name == current_tag_name and tag_name != 'O':
                current_entity_tokens.append(token.replace('##', ''))
            else:
                if current_entity_tokens and current_tag_name in desired_tag_names:
                    extracted_words_list.append("".join(current_entity_tokens))
                
                if tag_name in desired_tag_names:
                    current_entity_tokens = [token.replace('##', '')]
                    current_tag_name = tag_name
                else:
                    current_entity_tokens = []
                    current_tag_name = None

        if current_entity_tokens and current_tag_name in desired_tag_names:
            extracted_words_list.append("".join(current_entity_tokens))

        return extracted_words_list
        
    except Exception as e:
        print(f"[NER Inference Error] Inference error: {e}")
        return []

if __name__ == "__main__":
    print("Testing NER...")
    # 테스트 코드
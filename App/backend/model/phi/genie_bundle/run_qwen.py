import argparse
import sys
import json
import logging

import sys, os
print(f"[RUN_QWEN_V2] __file__ = {__file__}", file=sys.stderr)
print(f"[RUN_QWEN_V2] argv    = {sys.argv}", file=sys.stderr)
print(f"[RUN_QWEN_V2] cwd     = {os.getcwd()}", file=sys.stderr, flush=True)

# 로깅 레벨을 높여 허깅페이스/파이토치 메시지를 숨깁니다.
logging.basicConfig(level=logging.ERROR)

# PyTorch가 없으면 transformers가 경고를 출력하므로, 강제로 모듈 로딩을 시도해봅니다.
try:
    import torch
except ImportError:
    print("LLM 처리 중 오류 발생: None of PyTorch, TensorFlow >= 2.0, or Flax have been found. Models won't be available and only tokenizers, configuration and file/data utilities can be used.")
    sys.exit(1) # PyTorch 없으면 즉시 종료

# -----------------------------
# 1. Argument Parsing
# -----------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--text", type=str, required=True, help="Inference할 프롬프트 텍스트")
parser.add_argument("--model-path", type=str, required=True, help="LLM 모델 파일이 포함된 루트 경로")
args = parser.parse_args()

# -----------------------------
# 2. 모델 경로 설정
# -----------------------------
# model-path 인자로 전달받은 MODEL_ROOT_DIR 하위의 모델 폴더를 사용
QWEN_MODEL_DIR = os.path.join(args.model_path, "phi", "genie_bundle")

# -----------------------------
# 3. 모델 로드 및 추론
# -----------------------------
def run_inference(prompt_text: str):
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        # 모델 및 토크나이저 로드
        tokenizer = AutoTokenizer.from_pretrained(QWEN_MODEL_DIR, trust_remote_code=True)
        
        # CPU로 모델 로드 (NPU가 사용 불가능한 경우 대비)
        model = AutoModelForCausalLM.from_pretrained(
            QWEN_MODEL_DIR,
            device_map="cpu", # CPU 로드 강제
            torch_dtype=torch.bfloat16,
            trust_remote_code=True
        ).eval()

        # 프롬프트 구성
        # Qwen-VL-Chat 모델의 기본 포맷을 따름
        messages = [
            {"role": "user", "content": prompt_text}
        ]
        text_prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        # 추론
        input_ids = tokenizer([text_prompt], return_tensors="pt").input_ids
        
        with torch.no_grad():
            output_ids = model.generate(
                input_ids,
                max_new_tokens=256,
                do_sample=False,
                eos_token_id=tokenizer.eos_token_id
            )

        # 결과 디코딩 및 출력
        response = tokenizer.decode(output_ids[0][input_ids.shape[1]:], skip_special_tokens=True)
        print(response.strip())

    except Exception as e:
        # LLM 처리 중 발생하는 모든 예외를 잡아서 표준 에러(stderr)로 출력
        # main.py에서 이 stderr를 받아서 클라이언트에게 전달하게 됩니다.
        print(f"An error occurred during LLM inference: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_inference(args.text)
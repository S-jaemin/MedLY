import os
import sys
import gdown
import json
import zipfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.lib import colors
from fastapi import HTTPException
import tempfile
import re

#기존 코드
import asyncio
import datetime
import subprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import sys
import pyautogui
import pytesseract
import time
from datetime import datetime
from PIL import Image
import cv2
import numpy as np
from model.ner.NER import extract_medical_terms

# --- 기본 설정 ---

if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def get_root_dir():
    return os.path.dirname(os.path.abspath(__file__))
    
ROOT_DIR = get_root_dir()
STATIC_DIR = os.path.join(ROOT_DIR, "static")
INDEX_HTML = os.path.join(STATIC_DIR, "index.html")
HISTORY_HTML = os.path.join(STATIC_DIR, "history.html")

def get_model_root_dir():

    env_path = os.environ.get("MEDLY_MODEL_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    real_model_path = r"C:\Syaptix\App\backend_deploy\model"
    if os.path.exists(real_model_path):
        return real_model_path

    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
        internal_model_path = os.path.join(base_path, "model")
        if os.path.exists(internal_model_path):
            return internal_model_path

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")

MODEL_ROOT_DIR = get_model_root_dir()

QWEN_SCRIPT = os.path.join(MODEL_ROOT_DIR, "phi", "genie_bundle", "run_qwen.py")

MODEL_ZIP_ID = "1HGBEnr81kkMezPws7z3t7aSw-kECTPJ"

global MODEL_IS_READY
MODEL_IS_READY = False

try:
    import win32gui
    PYWIN32_AVAILABLE = True
except ImportError:
    print("***** pywin32 모듈을 찾을 수 없습니다. (pip install pywin32) *****")
    PYWIN32_AVAILABLE = False

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def get_tesseract_path():
    return os.path.join(MODEL_ROOT_DIR, 'tesseract-portable', 'tesseract.exe')

def register_dll_path_for_npu():
    # DLL들이 있는 폴더 경로 (모델 엔진 파일들이 압축 해제된 폴더)
    dll_folder = os.path.join(MODEL_ROOT_DIR, 'phi', 'genie_bundle')
    
    if os.path.exists(dll_folder):
        
        # 1. (권장) Python 3.8+의 공식 경로 추가 함수 사용
        if hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(dll_folder)
                print(f"[NPU-DLL] add_dll_directory 성공: {dll_folder}")
            except Exception as e:
                print(f"[NPU-DLL] add_dll_directory 실패 (권한 문제일 수 있음): {e}")

        # (os.environ['PATH']를 수정하여 QNN 실행 파일도 DLL을 찾도록 보장)
        os.environ['PATH'] = dll_folder + os.pathsep + os.environ['PATH']
        
    else:
        print(f"[NPU-DLL] 경고: DLL 폴더를 찾을 수 없음: {dll_folder}")

pytesseract.pytesseract.tesseract_cmd = get_tesseract_path()

def ensure_model_is_ready():
    """ 
    (수정) 6GB+ model.zip 하나만 확인하고 다운로드 및 압축 해제
    """
    os.makedirs(MODEL_ROOT_DIR, exist_ok=True)

    key_file = get_tesseract_path()

    if (os.path.exists(key_file)):
        print(f"모델 엔진을 찾았습니다: {MODEL_ROOT_DIR}")
        return True
    print("모델 엔진이 없습니다. 6GB+ model.zip 다운로드를 시작합니다...")
    zip_path = os.path.join(MODEL_ROOT_DIR, "model.zip")
    
    try:
        # 2. 6GB+ Zip 파일 다운로드
        gdown.download(id=MODEL_ZIP_ID, output=zip_path, quiet=False)
        
        # 3. Zip 압축 해제 (시간이 매우 오래 걸림)
        print("다운로드 완료. 6GB+ 압축 해제 중...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(MODEL_ROOT_DIR) # 'MODEL_ROOT_DIR'에 압축 해제
        
        # 5. 다운로드한 Zip 파일 삭제
        os.remove(zip_path)
        print("모델 엔진 준비 완료.")
        return True
        
    except Exception as e:
        print(f"치명적 오류: 모델 다운로드/압축 해제 실패: {e}")
        if os.path.exists(zip_path): os.remove(zip_path)
        return False

FALLBACK_REGION_LEFT = 0
FALLBACK_REGION_TOP = 90
FALLBACK_REGION_WIDTH = 2700
FALLBACK_REGION_HEIGHT = 90
FALLBACK_REGION = (FALLBACK_REGION_LEFT, FALLBACK_REGION_TOP, FALLBACK_REGION_WIDTH, FALLBACK_REGION_HEIGHT)

def get_live_caption_region(window_title="Live Captions"):
    """
    Windows API를 사용해 'Live Captions' 창의
    (x, y, 너비, 높이) 좌표를 찾습니다.
    """
    if not PYWIN32_AVAILABLE:
        return None # pywin32 없으면 None 반환
    try:
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd == 0:
            return None # 창을 못 찾으면 None 반환
            
        rect = win32gui.GetWindowRect(hwnd)
        x = rect[0]; y = rect[1]
        width = rect[2] - x; height = rect[3] - y
        
        return (x, y, width, height) # 찾았으면 좌표 반환
        
    except Exception:
        return None

conversations_db = []
unique_terms = set()
full_transcript_store = "" 

# --- OCR 및 LLM 처리 함수 ---
def capture_and_ocr(region):
    screenshot = pyautogui.screenshot(region=region)
    screenshot_np = np.array(screenshot)
    gray_image = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)
    _, binary_image = cv2.threshold(gray_image, 128, 255, cv2.THRESH_BINARY_INV)
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(binary_image, lang='kor+eng', config=custom_config)
    return text.strip()

def _clean_prompt_for_llm(prompt: str) -> str:
    """LLM 프롬프트에서 줄바꿈/중복 공백/문제 문자 정리"""
    if not isinstance(prompt, str):
        prompt = str(prompt)
    prompt = prompt.replace("\n", " ")
    prompt = re.sub(r"\s+", " ", prompt)
    prompt = prompt.replace('"', "'").replace("\\", "")
    # 여기서는 길이 자르지 않는다. (요약/정의 쪽에서 따로 컨트롤)
    return prompt.strip()

def _truncate_keep_tail(text: str, max_chars: int = 4000) -> str:
    """너무 긴 transcript를 LLM에 넣기 전에, 끝에서 max_chars만 남기기."""
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()
    if len(text) <= max_chars:
        return text
    # 최근 대화가 더 중요하니까, 마지막 max_chars만 사용
    clipped = text[-max_chars:]
    print(f"[LLM] Warning: Transcript truncated to last {max_chars} characters.")
    return clipped

def run_llm(prompt: str):
    """
    기존: sys.executable + run_qwen.py 로 서브 Python 프로세스 실행
    변경: genie-t2t-run.exe 를 직접 호출해서 LLM 결과를 받는 방식.
    → backend.exe 를 다시 띄우지 않으므로 8000 포트 충돌이 사라진다.
    """
    global MODEL_IS_READY, MODEL_ROOT_DIR

    if not MODEL_IS_READY:
        return "오류: 모델이 준비되지 않았습니다. 앱을 다시 시작하세요."
    if not prompt:
        return ""

    # ===== DEBUG 로그 (지금처럼 상황 체크용) =====
    print("=" * 80)
    print("[PY_BACKEND] run_llm (genie exe) invoked")
    print(f"[PY_BACKEND] PID              = {os.getpid()}")
    print(f"[PY_BACKEND] frozen           = {getattr(sys, 'frozen', False)}")
    print(f"[PY_BACKEND] MODEL_ROOT_DIR   = {MODEL_ROOT_DIR}")
    print(f"[PY_BACKEND] raw prompt length= {len(prompt)}")
    print("=" * 80, flush=True)

    # 프롬프트 정리
    user_text = _clean_prompt_for_llm(prompt)

    # genie 번들 경로
    bundle_dir = os.path.join(MODEL_ROOT_DIR, "phi", "genie_bundle")
    executable_path = os.path.join(bundle_dir, "genie-t2t-run.exe")
    base_config_path = os.path.join(bundle_dir, "genie_config.json")

    if not os.path.exists(executable_path):
        return f"LLM 엔진 실행 파일을 찾을 수 없습니다: {executable_path}"
    if not os.path.exists(base_config_path):
        return f"LLM 설정 파일을 찾을 수 없습니다: {base_config_path}"

    # DLL 경로 보강 (startup에서 이미 했더라도 한 번 더 해도 무해)
    env = os.environ.copy()
    env["PATH"] = bundle_dir + os.pathsep + env.get("PATH", "")

    temp_config_path = None

    try:
        # 1) 기본 config 로드
        with open(base_config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        # 2) ctx-bins 상대 경로 → MODEL_ROOT_DIR 기준 절대 경로로 치환
        bins = config_data["dialog"]["engine"]["model"]["binary"]["ctx-bins"]
        new_bins = [os.path.join(MODEL_ROOT_DIR, fname) for fname in bins]
        config_data["dialog"]["engine"]["model"]["binary"]["ctx-bins"] = new_bins

        # 3) 수정된 config를 임시 파일로 저장
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as tmp:
            json.dump(config_data, tmp, indent=4)
            temp_config_path = tmp.name

        # 4) 최종 프롬프트 구성
        #    (여기서 prompt는 이미 "Summarize for patient..." 같은 형태로 들어오므로
        #     우리는 system role만 얹어주고 user 메시지는 그대로 사용)
        full_prompt = (
            "<|im_start|>system\n"
            "You are a helpful medical AI assistant.\n"
            "<|im_end|>\n"
            "<|im_start|>user\n"
            f"{user_text}\n"
            "<|im_end|>\n"
            "<|im_start|>assistant\n"
        )

        cmd = [executable_path, "-c", temp_config_path, "-p", full_prompt]

        print("[PY_BACKEND] Spawning genie-t2t-run.exe")
        print(f"[PY_BACKEND]   cmd = {cmd}")
        print(f"[PY_BACKEND]   cwd = {bundle_dir}", flush=True)

        result = subprocess.run(
            cmd,
            cwd=bundle_dir,
            env=env,
            capture_output=True,
            text=True,
            encoding="latin-1",
        )

        print(f"[PY_BACKEND] genie exe finished. returncode={result.returncode}")
        out_snip = (result.stdout or "")[:400]
        err_snip = (result.stderr or "")[:400]
        print(f"[PY_BACKEND] stdout[:400] =\n{out_snip if out_snip else '<EMPTY>'}")
        print(f"[PY_BACKEND] stderr[:400] =\n{err_snip if err_snip else '<EMPTY>'}", flush=True)

        # 실행 자체가 실패한 경우
        if result.returncode != 0 and result.stderr:
            return f"LLM 처리 중 오류 발생: {result.stderr.strip()}"

        # 5) 출력 파싱
        raw_output = result.stdout or ""
        start_marker = "[BEGIN]:"
        end_marker = "[END]"

        if start_marker in raw_output and end_marker in raw_output:
            part_after = raw_output.split(start_marker, 1)[1]
            extracted = part_after.split(end_marker, 1)[0]
            return extracted.strip()

        # 마커 없는 경우 fallback: assistant 태그 뒤만 긁기
        if "<|im_start|>assistant" in raw_output:
            return raw_output.split("<|im_start|>assistant")[-1].strip()

        # 그래도 없으면 전체 stdout 정리해서 반환
        return raw_output.strip()

    except Exception as e:
        print(f"[PY_BACKEND] Exception in run_llm (genie): {e!r}", flush=True)
        return f"An error has occured while processing LLM: {e!r}"

    finally:
        if temp_config_path and os.path.exists(temp_config_path):
            try:
                os.remove(temp_config_path)
            except OSError:
                pass

async def process_llm_and_save(websocket: WebSocket, text: str):
    # 1) 너무 긴 transcript는 끝에서 4000자만 남긴다.
    MAX_TRANSCRIPT_CHARS = 4000
    safe_text = _truncate_keep_tail(text, MAX_TRANSCRIPT_CHARS)

    # 2) 요약 프롬프트 구성
    prompt = f"Summarize for patient in prose less than 250 words: {safe_text}"

    # 3) LLM 호출
    llm_output = run_llm(prompt)

    # 4) 결과 저장 + 전송
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    response = {
        "type": "summary_result",
        "input_text": safe_text,  # 요약에 실제로 사용된 텍스트를 저장하는 게 디버깅에 좋음
        "output": llm_output,
        "timestamp": timestamp
    }
    conversations_db.append(response)
    await websocket.send_json(response)

@app.on_event("startup")
def on_startup():
    global MODEL_IS_READY
    MODEL_IS_READY = ensure_model_is_ready()
    
    if not MODEL_IS_READY:
        print("***** 모델 준비에 실패하여 LLM 기능을 사용할 수 없습니다. *****")
    else:
        register_dll_path_for_npu()
        print(f"***** 모델이 준비되었습니다. (경로: {MODEL_ROOT_DIR}) *****")

# --- 웹 페이지 라우팅 ---
@app.get("/")
def get_status():
    global MODEL_IS_READY
    
    if not MODEL_IS_READY:
        raise HTTPException(
            status_code=503,
            detail="Service Unavailable: AI Models are still loading or downloading."
        )
    
    # 모델이 준비되었으면 200 OK 반환
    return {"status": "ok", "message": "Models are ready."}

# --- 핵심 웹소켓 파이프라인 ---
async def live_transcription_pipeline(websocket: WebSocket):
    global unique_terms, full_transcript_store
    buffer = []; last_processed_text = ""; last_seen_text = ""
    prefix_to_ignore = None; capture_count = 0

    try:
        while True:
            # 1초에 한 번 실행 (창 찾기 및 OCR)
            await asyncio.sleep(1.0) 
            
            # 1. 'Live Captions' 창 위치 찾기 시도
            capture_region = get_live_caption_region()
            
            # 2. 창을 찾지 못했으면, 하드코딩된 폴백 영역 사용
            if capture_region is None:
                capture_region = FALLBACK_REGION
            
            # 3. 결정된 영역(자동 또는 폴백)으로 캡처
            current_text = capture_and_ocr(capture_region).replace("\n", " ").strip()
            
            if current_text and current_text != last_seen_text:
                if capture_count < 1:
                    capture_count += 1;
                    prefix_to_ignore = current_text; last_seen_text = current_text
                    continue
                
                clean_current_text = current_text
                if prefix_to_ignore and clean_current_text.startswith(prefix_to_ignore):
                    clean_current_text = clean_current_text[len(prefix_to_ignore):].strip()

                if not buffer:
                    buffer.append(clean_current_text)
                else:
                    new_part = clean_current_text
                    if last_processed_text in new_part: new_part = new_part.replace(last_processed_text, "", 1).strip()
                    if new_part: buffer.append(new_part)

                full_transcript_store = " ".join(buffer)
                last_processed_text = clean_current_text; last_seen_text = current_text
                ner_terms = extract_medical_terms(full_transcript_store)
                unique_terms.update(ner_terms)
                
                await websocket.send_json({
                    "type": "live_text", "sentence": full_transcript_store,
                    "ner_terms": ner_terms, "unique_terms": sorted(list(unique_terms))
                })
                
    except (WebSocketDisconnect, asyncio.CancelledError):
        print("Live Transcription: Pipeline task cancelled or client disconnected.")
# --- 웹소켓 엔드포인트 (안정성 강화) ---
@app.websocket("/ws/ocr_pipeline")
async def websocket_ocr_endpoint(websocket: WebSocket):
    await websocket.accept()
    transcription_task = None
    global unique_terms, full_transcript_store

    while True:
        try:
            message = await websocket.receive_text()
            data = json.loads(message)
            command = data.get("command")

            if command == "start":
                if transcription_task is None or transcription_task.done():
                    unique_terms.clear()
                    full_transcript_store = ""
                    transcription_task = asyncio.create_task(live_transcription_pipeline(websocket))

            elif command == "stop_session":
                if transcription_task:
                    transcription_task.cancel()
                    transcription_task = None
                
                final_ner_terms = extract_medical_terms(full_transcript_store)
                final_unique_terms = sorted(list(set(final_ner_terms)))
                
                await websocket.send_json({
                    "type": "final_update",
                    "sentence": full_transcript_store,
                    "ner_terms": final_unique_terms,
                    "unique_terms": final_unique_terms
                })
                
                await websocket.send_json({"type": "processing_llm"})
                await process_llm_and_save(websocket, full_transcript_store)

            elif command == "define_term":
                term = data.get("term")
                level = data.get("level", "Adult")
                prompt_map = {
                    "Child": f"Provide a simplified explanation for the medical term '{term}' in very simple terms for a child. The explanation should be no more than three sentences.",
                    "Student": f"Provide a detailed explanation for the medical term '{term}' for a high school student. The explanation should be no more than three sentences.",
                    "Adult": f"Provide a clear and concise definition of the medical term '{term}'. The explanation should be no more than three sentences."
                }
                prompt = prompt_map.get(level, prompt_map["Adult"])
                definition = run_llm(prompt)
                await websocket.send_json({"type": "term_definition", "term": term, "definition": definition})

        except WebSocketDisconnect:
            print("Client disconnected.")
            if transcription_task:
                transcription_task.cancel()
            break  # 루프를 탈출하여 핸들러를 정상적으로 종료

        except Exception as e:
            # WebSocketDisconnect 이외의 모든 예외를 처리하여 연결을 유지합니다.
            print(f"Websocket has been disconnected: {e}")
            # 선택적으로 클라이언트에게 에러를 알릴 수 있습니다.
            # await websocket.send_json({"type": "error", "message": str(e)})

# --- PDF 생성 및 내보내기 ---
def _draw_paragraph(c, text, x, y, max_width, leading=14, font_name="Helvetica", font_size=11):
    c.setFont(font_name, font_size)
    lines = simpleSplit(text or "", font_name, font_size, max_width)
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
        if y < 30 * mm:  # 하단 마진 도달 시 새 페이지
            c.showPage()
            c.setFont(font_name, font_size)
            y = A4[1] - 20 * mm
    return y
from fastapi import Body

@app.post("/api/export_pdf")
async def export_pdf(payload: dict = Body(...)):
    """
    요청 바디 예시:
    {
      "title": "MedLY AI Report",
      "transcript": "Full conversation text",
      "summary": "Summary text",
      "terms": ["term1", "term2"],
      "definition_term": "selected term",
      "definition": "Definition text",
      "conversation_label": "Diagnosis"   # 선택(기본값: Diagnosis)
    }
    """

    # -------- 입력 파싱 --------
    title = payload.get("title") or "Medly AI Report"
    transcript = payload.get("transcript") or ""
    summary = payload.get("summary") or ""
    terms = payload.get("terms") or []
    definition_term = payload.get("definition_term") or ""
    definition = payload.get("definition") or ""
    conversation_label = payload.get("conversation_label", "Diagnosis")  # 기존 'Patient Conversation' 대체

    # -------- 파일명/경로 --------
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fname = f"medly_{int(time.time())}.pdf"
    fpath = os.path.join(STATIC_DIR, fname)

    # -------- PDF 캔버스 생성 --------
    c = canvas.Canvas(fpath, pagesize=A4)
    width, height = A4

    # -------- 색상 팔레트 --------
    SECTION_COLORS = {
        "Summary": colors.HexColor("#0045a0"),             # 청록
        conversation_label: colors.HexColor("#0045a0"),    # 파랑 (Diagnosis 등)
        "Key Terms": colors.HexColor("#0045a0"),           # 보라
        "Key Term Definition": colors.HexColor("#0045a0"), # 오렌지 브라운
    }
    HEADER_TITLE_COLOR = colors.HexColor("#003870")
    HEADER_META_COLOR = colors.HexColor("#132d50")

    # -------- 헬퍼: 섹션 제목 그리기 --------
    def draw_section_title(text: str, x: float, y: float) -> float:
        c.setFont("Helvetica-Bold", 15)
        c.setFillColor(SECTION_COLORS.get(text, colors.black))
        c.drawString(x, y, text)
        c.setFillColor(colors.black)  # 본문은 검정으로 복귀
        return y - 8*mm               # 제목-본문 간격

    # -------- 헤더 --------
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(HEADER_TITLE_COLOR)
    c.drawString(20*mm, height - 20*mm, title)

    c.setFont("Helvetica", 11)
    c.setFillColor(HEADER_META_COLOR)
    c.drawString(20*mm, height - 26*mm, f"Generated at: {ts}")
    c.setFillColor(colors.black)

    y = height - 36*mm

    # -------- 섹션: Summary --------
    y = draw_section_title("Summary", 20*mm, y)
    y = _draw_paragraph(c, summary, 20*mm, y, max_width=170*mm)

    # -------- 섹션: Diagnosis(=conversation_label) --------
    y -= 5*mm
    y = draw_section_title(conversation_label, 20*mm, y)
    y = _draw_paragraph(c, transcript, 20*mm, y, max_width=170*mm)

    # -------- 섹션: Key Terms --------
    if terms:
        y -= 5*mm
        y = draw_section_title("Key Terms", 20*mm, y)
        y = _draw_paragraph(c, ", ".join(terms), 20*mm, y, max_width=170*mm)

    # -------- 섹션: Key Term Definition --------
    if definition_term or definition:
        y -= 5*mm
        y = draw_section_title("Key Term Definition", 20*mm, y)
        y = _draw_paragraph(
            c,
            f"**{definition_term}**\n{definition}".strip(),
            20*mm,
            y,
            max_width=170*mm
        )

    # -------- 종료/저장 --------
    c.showPage()
    c.save()

    # 정적 URL 반환
    return {"url": f"/static/{fname}"}

if __name__ == "__main__":
    import uvicorn
    # 멀티프로세싱(pytesseract 등) 사용 시 윈도우에서 필수
    import multiprocessing
    multiprocessing.freeze_support() 
    
    print("Starting Medly Backend Server...")
    # reload 옵션은 exe에서 불가능하므로 제거해야 함
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
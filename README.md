<div align="center">

# 🏥 Medly: A Patient-Friendly Medical Phraseology App

**An on-device AI app that provides real-time explanations of medical terms to improve communication between patients and doctors.**

<p>
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/ONNX--Runtime-lightgrey?style=for-the-badge&logo=onnx&logoColor=black" alt="ONNX Runtime">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="License: MIT">
</p>

</div>

<div align="center">
  
### 🎬 **Execution Video**
</div>
<div align="center">
  <a href="https://www.youtube.com/watch?v=cnXvFwt4Krc">
  <img src="https://i.ytimg.com/vi/cnXvFwt4Krc/hqdefault.jpg" alt="Watch the video" />
</a>
</div>


---

### **1. Purpose**

> **"Difficult medical terms are no longer a barrier."**

<mark>**Medly**<mark> is an innovative **on-device AI** solution that leverages the  
<mark>**NPU performance of the Snapdragon X Elite**</mark>  
to analyze speech in real time and instantly convert complex medical jargon into easy-to-understand everyday language for patients.  

In this project, we developed a service that:

- Summarizes **specialized medical terminology** mentioned during consultations by medical professionals  
- Adjusts the content to match each patient’s **individual comprehension level**  
- Tags **key medical terms** and provides **easy-to-understand explanations**

<br>

The system is built for  **Qualcomm’s Snapdragon X Elite** and utilizes a **fine-tuned NER model** along with the **Qwen2.5-7B** model.  

Designed as an **edge-device application**, it operates smoothly in **offline environments**.  
For the best user experience, we recommend using <mark>**Microsoft Live Caption**</mark>.

---

### ⚙️ <strong>NPU Leverage</strong>

- **Ultra-low Latency Performance**  
  By leveraging **8-bit quantized models** from **Qualcomm AI Hub**,  
  the system achieves significantly faster and more efficient **speech recognition** and **medical term tagging**  
  compared to traditional CPU or GPU inference.  

  This allows patients and healthcare providers to receive **real-time explanations**  
  with virtually **no latency**.  

  > _Parallelization of the **Live Caption** feature, OCR pipeline, and LLM backend logic  
  > will be added in a future update._

<br>

- **High Energy Efficiency**  
  Its low-power design allows the AI to run continuously for approximately  
  **10–12 hours** on a standard Microsoft laptop  
  without significant battery drain.

<br>

- **Enhanced Security & Data Privacy**  
  All processes—including patient responses, consultation data, AI computations,  
  and generated outputs—are handled **entirely on the edge device**,  
  <strong>**ensuring complete data isolation**<strong>
  and preventing any risk of external data leakage.

---

## 💡Key Features
| Feature | Description |
|   ---   | --- |
| **🎙️ Real-time STT** | We used Microsoft’s Live Caption feature in our build and test environment. |
| **🧬 Terminology Recognition** | Accurately identifies and tags medical-related professional terms from the text. |
| **💡 Simplified Explanations** | AI analyzes the meaning of recognized professional terms to provide easy-to-understand explanations and summaries. |
| **📜 Comprehensive Summary** | Provides a complete summary of the entire voice conversation. |
| **📄 PDF Report Generation** | Generates a PDF report that summarizes your diagnosis and allows for printing. |
| **👨‍👩‍👧‍👦 Adjustable Difficulty** | Enables setting the explanation difficulty level (Child, Student, Adult) by adjusting the LLM's prompts. |

---
## 🛠️ Tech Stack
**💻 Hardware Requirements (Tested device)**
```text
Chip: Snapdragon® X Elite X1E-80-100
OS: Windows 11 Home
Memory: 16 GB +
Storage: 512 GB eUFS
NPU: Qualcomm® Hexagon™ NPU
```
**📚 Software Requirements**
```text
Transcription: Live Caption & Tesseract OCR
Named Entity Recognition: d4data/biomedical-ner-all
LLM Provider: Qualcomm QNN
Chat Model: Qwen2.5_7B_Instruct
Python: 3.12.X (Recommended)
```
---
## ⚙️ Manual Application Build (Safe Method)

"Please download the latest version of Node.js."
 - [Official Page](https://nodejs.org/ko)

This application utilizes open-source models (such as Qwen, NER, and OCR) that have been optimized for NPU performance through conversion to the ONNX file format.

Because some of these large model files exceed GitHub's 50MB size limit, the complete installer is provided via an external link. If downloading from the provided links during app execution is not possible, please manually download the model files to the specified location by following the manual below.

- 1. [Download the installer from Google Drive](https://drive.google.com/file/d/1HGBEnr81kkMezPws7z3t7aSw-kECTPJU/view)

- ### 📁 Folder Structure

Please place the downloaded `model` folder inside the `backend_deploy` directory as shown below:

```text
PROJECT_ROOT/
├─ .gitignore
├─ config.json
└─ App/
   ├─ package.json
   ├─ electron/
   ├─ dist/
   ├─ backend/
   ├─ backend_deploy/
   │  └─ model/  ⬅️⬅️⬅️ Here!
   └─ ...

- 2. zip-off the file
 
- 3. make the venv and download requirements In **backend folder**.
 
- 4. Run the command below **In App folder**.
    ```text
     npm install
     ```

- 5. Run the command below **In backend**.
    ```text
     pyinstaller --noconfirm --onedir --console --name "backend" --add-data "static;static" --hidden-import "uvicorn.logging" --hidden-import "uvicorn.loops" --hidden-import "uvicorn.loops.auto" --hidden-import "uvicorn.protocols" --hidden-import "uvicorn.protocols.http" --hidden-import "uvicorn.protocols.http.auto" --hidden-import "uvicorn.lifespan" --hidden-import "uvicorn.lifespan.on" --hidden-import "engineio.async_drivers.aiohttp" main.py
     ```

- 6. Run the command below.
    ```text
     npm run build
     ```

---
### 🛠 Manual Setup (Built Application)

1. If you have already built the app, double-click the `Medly Setup 1.0.0.exe` file in the `dist` folder to start the installation.
2. After installation, double-click the installed application to run it.
3. Once the initial screen has loaded, start **Live Caption** using the shortcut `Ctrl` + `Win` + `L`, then go to **Settings → Position → Above the screen**.

> ※ If Live Caption displays text in **two lines**, the OCR pipeline may not recognize the text correctly.  
>    Please adjust the **font size** or the **height of the Live Caption window** so that the caption text is transcribed on **a single line**.

## ▶ Execution Scenario

- Click **Start Recording** to begin a new session.  
- As you speak, the conversation is transcribed in real time and displayed in the **Diagnosis** area.  
- When the conversation is finished, click **Stop Recording**.  
- After a short moment, a summary of the conversation is generated in the **Summary** area, and important medical terms appear under **Key Terms**.  
- Click any term in the **Key Terms** list to see its definition in the **Definition** panel on the right.  
- Adjust the explanation level by selecting **Child**, **Student**, or **Adult**, depending on the desired reading difficulty.  
- Click **Download PDF** to save a report containing the full transcript, summary, and key terms from the session.  
- To clear the current results and start a new recording, click **New Session** (the **Stop** button changes to **New Session** after a session ends).

---
## 👨‍💻 Synaptix : Team Members

- Jaemin Song (jaemin0003@gmail.com)
- Jooyeob Han (hanjooyeob@korea.ac.kr)
- Hyunseo Lee (info.laurenlee28@gmail.com)
- Joon Lim (slow0209@korea.ac.kr)
- Hyeeun Bae (baehappygirl@gmail.com)


---
## 📜 License
MIT License

Copyright (c) <2025> <Synaptix>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

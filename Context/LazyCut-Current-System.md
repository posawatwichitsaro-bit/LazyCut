# LazyCut — ภาพรวมระบบปัจจุบัน

ตรวจเมื่อ 18 พฤศจิกายน 2026 จาก checkout ที่ LazyCut สาขา `main` คอมมิต `325ad2a0e2c25c38bea641d494204d53b292b851` ที่เพิ่มการจับ killfeed ภาษาไทย สถานะ Git สะอาด ณ เวลาที่ตรวจ เอกสารนี้อ้างอิงซอร์สใน checkout ดังกล่าว

## ระบบทำอะไร

LazyCut เป็นเครื่องมือบนเครื่องสำหรับนำคลิปเกม FPS มาจัดเป็น montage แนวตั้ง 9:16 หรือแนวนอน 16:9 ระบบอ้างอิงคลิปด้วยพาธต้นฉบับ ใช้ OpenCV หาเหตุการณ์ใน Valorant แล้วใช้ FFmpeg ตัดและประกอบวิดีโอ เก็บข้อมูลคลิปและงานใน SQLite ผลงานเป็น MP4 พร้อมไฟล์ข้อความ chapters

## เส้นทางจากคลิปต้นฉบับถึงผลงาน

1. เปิด `start.bat` จากโฟลเดอร์โครงการ สคริปต์สร้าง `.venv` และลง dependencies ในครั้งที่ยังไม่มี Python ใน venv จากนั้นเปิดเบราว์เซอร์และรัน FastAPI ผ่าน Uvicorn ที่ `127.0.0.1:8000` โค้ดเริ่มระบบสร้างตาราง SQLite และเริ่ม Watchdog เมื่อมีพาธโฟลเดอร์ที่ใช้ได้ หน้า Studio ใช้ HTML/CSS/JavaScript ใน `main.py` เป็นค่าเริ่มต้น
2. ตั้ง Watch Folder ใน Settings แล้วใช้ Rescan Folder เพื่อขึ้นทะเบียนคลิปที่มีอยู่ หรือให้ Watchdog จับไฟล์ใหม่และไฟล์ที่เปลี่ยนจากเหตุการณ์บนระบบไฟล์ ตัวเฝ้าโฟลเดอร์รอให้ขนาดไฟล์คงที่ก่อนอ่าน และรองรับ MP4, MKV, MOV และ AVI ตามค่าเริ่มต้น นอกจากนี้ยังมี API นำเข้าด้วยพาธไฟล์
3. Studio Feed แสดงคลิปและกรองตามจำนวน kill หรือสถานะ verified ได้ Preview เล่นคลิปต้นฉบับผ่าน API และเรียกวิเคราะห์ไฮไลต์ ตัวตรวจจับใช้ ROI ตาม preset และใช้ภาพแม่แบบคำว่า “ฉัน” ประกอบกับสีขอบและการ์ดเพื่อหา kill ของผู้เล่น พร้อมตรวจสัญลักษณ์ headshot
4. Generate Montage สร้างงาน `QUEUED` ใน SQLite แล้วส่งเข้า FastAPI BackgroundTasks ใน process เดียวกัน ตัว compositor เปิดงานเป็น `PROCESSING` และวิเคราะห์ไฟล์ที่เลือกใหม่ผ่าน `HighlightCurator` โดยใช้ killfeed, headshot และระดับพลังงานเสียงในการประเมินเหตุการณ์ ค่าเริ่มต้นของช่วงภาพในเส้นทางนี้คือก่อนเหตุการณ์ 4.5 วินาที หลัง 2.5 วินาที และจัดกลุ่มเหตุการณ์ที่ห่างกันไม่เกิน 3.5 วินาที
5. งานเรียงช่วงตัดตามลำดับเวลาที่ตีความจากชื่อหรือพาธไฟล์และเวลาเริ่มในคลิป แล้วตัดตามงบเวลาที่ขอ โดยมีเพดาน 900 วินาที หากไม่พบ kill ในคลิปที่เลือกทั้งหมด ระบบใช้ช่วงต้นของไฟล์ที่ยังอยู่เป็นทางสำรอง เมื่อมีช่วง kill ที่ใช้ได้ คลิปที่ไม่มีช่วงดังกล่าวจะถูกข้าม
6. ระบบตรวจพื้นที่ดิสก์และเรียก FFmpeg เพื่อประกอบวิดีโอ ใช้ preset จัด HUD สำหรับแนวตั้ง และอ่าน Vibe เพื่อกำหนด audio ducking กับ fade-out เมื่อมี BGM ที่ใช้ได้ การเลือก encoder แบบ auto ลอง NVENC → AMF → QSV → libx264 ส่วน FFmpeg ค้นจาก PATH → `bin/` → `imageio-ffmpeg`
7. งานที่สำเร็จเขียน MP4 และ TXT ลง `exports/` บันทึก `ReelExport` และเปลี่ยนเป็น `COMPLETED` ความผิดพลาดที่เข้าตัวจัดการของ compositor เปลี่ยนเป็น `FAILED` พร้อมข้อความ หน้า Studio อ่านสถานะด้วยการ polling และใช้ Reel Inspector แสดงผลที่พร้อมแล้ว เส้นทาง `/exports` ให้เบราว์เซอร์เข้าถึงไฟล์ส่งออก

## จุดเข้าใช้งานและข้อมูล

| ส่วน | จุดเข้าใช้งานหรือข้อมูล |
| --- | --- |
| Dashboard และ API | `backend/app/main.py` เชื่อม `api/clips.py`, `jobs.py`, `presets.py` และ `settings_router.py` |
| คลิป | `GET /api/clips`, `POST /api/clips/import`, `POST /api/clips/scan` และ `GET /api/clips/{id}/thumbnail`, `/stream`, `/analyze` |
| งานและผลลัพธ์ | `POST /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/export` |
| การตั้งค่าและทรัพยากร | `GET/POST /api/settings`, `GET /api/settings/hardware`, `/api/presets`, `/api/vibes` และ `/api/music` |
| การนำเข้าและตรวจจับ | `watcher/folder_watcher.py`, `watcher/process_guard.py`, `detection/killfeed_detector.py`, `detection/highlight_curator.py` ใต้ `backend/app/` |
| การประกอบงาน | `engine/compositor.py`, `engine/filter_graph.py`, `engine/ai_montage_director.py`, `engine/ai_router.py` ใต้ `backend/app/` |
| ไฟล์ตั้งค่า | ค่าเริ่มต้นใน `backend/app/core/config.py` และอ่าน `.env` ได้ มี preset `valorant_1080p` กับ Vibe `chill_memory`, `hype_montage`, `raw_clean` |
| ข้อมูลถาวร | `lazycut.db`, วิดีโอต้นฉบับที่อยู่ในตำแหน่งเดิม, BGM ใน `music/` และไฟล์ผลลัพธ์ใน `exports/` ตามค่าเริ่มต้น |

SQLite มี 4 ตารางหลักใน `backend/app/models/entities.py`

- `SourceClip` เก็บพาธที่มี unique index ชื่อไฟล์ ระยะเวลา ขนาด จำนวน kill และสถานะ verified เชื่อมหนึ่งต่อหลายกับ `KillEvent` ซึ่งเก็บเวลา ความมั่นใจ และชนิดเหตุการณ์
- `MontageJob` เก็บรายการ clip ID เป็น JSON รวมถึง preset, vibe, ระยะเวลาเป้าหมาย, สถานะ และ progress เชื่อมหนึ่งต่อหลายกับ `ReelExport` ซึ่งเก็บพาธไฟล์ อัตราส่วน ระยะเวลาที่ compositor คำนวณ และ metadata ของผลลัพธ์

## พฤติกรรมที่มีผลต่อการใช้งาน

| ประเด็น | สิ่งที่พบในซอร์ส |
| --- | --- |
| Game Process Guard | ใช้พักการสแกนหนักใน callback ของ Watchdog ระหว่างเกมทำงาน โดยขึ้นทะเบียนคลิปใหม่แบบยังไม่ verified เส้นทางสร้างงานและ compositor ไม่มีเงื่อนไขพักเรนเดอร์ตามสถานะเกม |
| การเลือกช่วงด้วย AI | compositor เรียงและจำกัดช่วงตัดด้วยโค้ดตามลำดับเวลา และใช้ `AIRouter(provider="none")` ให้ metadata จาก template โมดูล AI และ YouTube uploader มีอยู่ในซอร์ส โดย YouTube uploader ยังไม่ถูกเรียกในเส้นทางสร้าง montage |
| การแจ้งเตือน | หลังสร้างผลลัพธ์ compositor มีการเรียก Discord เมื่อกำหนด webhook ส่วน Telegram ไม่มีจุดเรียกในขั้นตอนเดียวกัน |
| การคงค่าตั้งค่า | Save & Watch เปลี่ยนค่าบน process ปัจจุบัน การเริ่มใหม่อ่านค่าตั้งต้นหรือ `.env` อีกครั้ง ค่า encoder ที่ resolve แล้วถูก cache จึงอาจยังใช้ค่าเดิมหลังปรับ Settings |
| ความต่อเนื่องของงาน | สถานะถูกเก็บใน SQLite แต่งานทำใน process ของ API ยังไม่มีเส้นทางกู้งานอัตโนมัติเมื่อรีสตาร์ต การ resolve FFmpeg เกิดก่อนตั้ง `PROCESSING` จึงอาจทิ้งงานไว้ที่ `QUEUED` หากเริ่ม compositor ไม่สำเร็จ |
| Preset และภาษา | คอมมิตนี้ใช้ภาพแม่แบบ “ฉัน” และ ROI ของ HUD การเลือก preset ของงานถูกส่งไปยัง filter แนวตั้ง ส่วน compositor สร้าง `HighlightCurator()` ด้วยค่าเริ่มต้น จึงควรตรวจทั้งการจับเหตุการณ์และการ crop แยกกันเมื่อเปลี่ยน preset ภาษา หรือสัดส่วนภาพ |

## หลักฐานและขอบเขตการตรวจ

- เครื่องพบ Python 3.14 จาก PATH ส่วน CI กำหนดทดสอบ Pytest บน Windows ด้วย Python 3.11, 3.12 และ 3.13 การรันบน Python 3.14 จึงยังไม่ได้ยืนยันจาก CI ใน checkout นี้
- ขณะตรวจไม่พบ `.venv`, `.env` หรือ `lazycut.db` ใน checkout และไม่พบ FFmpeg/FFprobe จาก PATH Python ที่ตรวจยังไม่มี FastAPI, SQLModel, OpenCV, imageio-ffmpeg และ pytest
- การตรวจครั้งนี้เป็นการอ่านซอร์สและตรวจสภาพแวดล้อมเบื้องต้น ยังไม่ได้ติดตั้ง dependencies, เปิด Studio, รัน pytest หรือเรนเดอร์คลิปจริง
- หากต้องยืนยันการใช้งานครบเส้นทาง ให้ทดสอบกับคลิป Valorant ภาษาไทยในโฟลเดอร์ทดสอบ ตรวจ Rescan และ Preview จากนั้นสร้างงานทั้ง 9:16 และ 16:9 แล้วเทียบสถานะใน Studio กับ MP4 และ TXT ที่ได้

## ตำแหน่งบันทึกเอกสาร

เก็บ Markdown ใหม่ที่จัดทำสำหรับงาน LazyCut ใน `Context/` เอกสารต้นฉบับของ repository เช่น `README.md`, `PROGRESS.md`, `GLOSSARY.md` และ ADR ยังอ้างอิงได้จาก checkout ตามโครงสร้างเดิม

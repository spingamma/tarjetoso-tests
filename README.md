# 🎭 Playwright + Pytest - Template de Automatización

¡Bienvenido al entorno de pruebas automatizadas! Este proyecto es una plantilla concisa para realizar pruebas de navegador utilizando **Playwright** y **Pytest**, con reportes visuales increíbles gracias a **Allure**.

Además, incluye herramientas para medir el rendimiento como **Locust** y **Lighthouse**, y un **Lector de Jira Cloud** para sincronizar tickets de QA. ¡Vamos a configurarlo paso a paso!

---

## 📋 Revisión Diaria de Jira para QA

La utilidad `scripts/jira_daily_review.py` obtiene todos los tipos de ticket de las columnas QA de tu tablero de Jira Cloud (por defecto `Ready for test/QA (Amb de STG)` y `Ready for Test/QA (en amb Dev)`, o configurables vía `JIRA_COLUMNS` / `--column`). Genera un reporte Markdown estructurado y copy-ready para revisar y alimentar contexto al chat de IA.

1. **Crear la configuración local** (el archivo resultante está ignorado por Git):
   ```bash
   cp .env.jira.example .env.jira
   # Editar .env.jira y completar JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN y JIRA_BOARD_ID
   ```

2. **Validar conexión, permisos y columnas del tablero:**
   ```bash
   python scripts/jira_daily_review.py doctor
   ```

3. **Generar/Actualizar el reporte Markdown:**
   ```bash
   python scripts/jira_daily_review.py update
   ```

El resultado se guarda en `artifacts/jira/jira_qa_daily.md`. Incluye resumen con enlaces rápidos, título, descripción en Markdown limpio, tipo de issue, assignee, reporter, comentarios en orden cronológico y lista de adjuntos. La escritura es atómica (no corrompe el reporte previo si la red o API falla) y es de solo lectura (no altera nada en Jira).

---

## 🛑 1. Requisitos Previos

Necesitas tener instalados **Python 3.10+**, **Node.js** y **Java JRE** (necesario para visualizar los reportes de Allure). Elige la sección según tu sistema operativo:

### 🪟 Windows (usando Scoop)
1. Instala **Scoop** si aún no lo tienes (abre PowerShell y corre):
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   irm get.scoop.sh | iex
   ```
2. Instala Python, Node.js, Java y Allure:
   ```powershell
   scoop install python nodejs-lts openjdk allure
   ```

### 🔵 Fedora Linux (usando DNF/NPM)
1. Instala Python, Node.js y Java Runtime Environment:
   ```bash
   sudo dnf install python3 python3-pip nodejs java-latest-openjdk-headless -y
   ```
2. Instala la herramienta de línea de comandos de Allure globalmente:
   ```bash
   sudo npm install -g allure-commandline --unsafe-perm=true
   ```

---

## 💻 2. Preparando el Entorno de Python

Primero, vamos a crear nuestro entorno virtual (nuestra "burbuja" de trabajo) para mantener limpias las dependencias.

1. **Abre tu terminal** en la carpeta de este proyecto.
2. **Crea el entorno virtual:**
   * **En Windows (PowerShell/CMD):**
     ```powershell
     python -m venv venv
     ```
   * **En Fedora / Linux:**
     ```bash
     python3 -m venv venv
     ```
3. **Activa el entorno virtual:**
   * **En Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate
     ```
     *(Si te da un error de permisos en PowerShell, ejecuta `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` y vuelve a intentarlo).*
   * **En Fedora / Linux:**
     ```bash
     source venv/bin/activate
     ```

---

## 📦 3. Instalación de Dependencias

Con el entorno virtual activado `(venv)`, instala los paquetes de Python y los navegadores web.

1. **Instala las librerías de Python:**
   *(Asegúrate de que el archivo `packages.txt` esté en la carpeta raíz)*
   * **En Windows / Fedora:**
     ```bash
     pip install -r packages.txt
     ```
2. **Instala los navegadores y dependencias de Playwright:**
   * **En Windows (PowerShell):**
     ```powershell
     python -m playwright install
     ```
   * **En Fedora / Linux:**
     ```bash
     python3 -m playwright install
     python3 -m playwright install-deps
     ```
     > [!IMPORTANT]
     > El comando `install-deps` es necesario en Linux para descargar las dependencias del sistema (librerías compartidas) que los navegadores embebidos de Playwright requieren para funcionar correctamente.

---

## 🛠️ 4. Instalación de Herramientas de Rendimiento (Lighthouse)

Lighthouse requiere Node.js para ejecutarse de manera local en el proyecto:

* **En Windows / Fedora:**
  ```bash
  npm install lighthouse
  ```

---

## 🚀 5. ¡A Correr las Pruebas!

> [!NOTE]
> Gracias a nuestro archivo `pytest.ini`, las pruebas funcionales están configuradas para ejecutarse con **Chrome**, generar reportes de **Allure**, y guardar **trazas en caso de fallo** automáticamente con un simple `pytest`.

Aquí tienes tu "hoja de trucos" con el flujo completo paso a paso (Funcional + Lighthouse + Locust + Reporte):

### Ejecución de pruebas
```bash
# 1. Pruebas Funcionales (E2E UI y API en Pytest)
python -m pytest tests/e2e/test_business_creation.py -n 0

# 2. Pruebas de Lighthouse (Rendimiento Web)
python -m pytest tests/performance/test_lighthouse.py --only-lighthouse

# 3. Pruebas de Locust (Pruebas de Carga API)
python -m locust -f tests/performance/locustfile.py --headless --users 10 --spawn-rate 2 --host https://example.com --html reporte-locust.html

# 4. Generar y abrir el reporte consolidado de Allure (UI + Lighthouse)
allure generate ./allure-results -o ./allure-report --clean
allure open ./allure-report
```

**⚙️ Ejecución General (CI/CD y Local)**
* Correr todas las pruebas con la configuración óptima:
  ```bash
  pytest
  ```
  *(Nota: Si en Windows recibes el error "An Application Control policy has blocked this file", usa `python -m pytest` en lugar de `pytest` en todos los comandos).*
* Correr en paralelo con N workers (requiere `pytest-xdist`):
  ```bash
  pytest -n 2
  ```
* Ignorar el paralelismo (ejecución secuencial clásica):
  ```bash
  pytest -n 0
  ```

**🖥️ Pruebas Funcionales Específicas**
* Correr un archivo específico:
  ```bash
  pytest tests/e2e/test_business_creation.py
  ```
* Simular un dispositivo móvil:
  ```bash
  pytest --browser_name device
  ```

**🐛 Depuración (Debugging)**
* Ver la ejecución en el navegador en tiempo real (Headed):
  ```bash
  pytest --headed -n 0
  ```
* Ver la ejecución MUY lenta para entender qué está fallando (1 segundo por acción):
  ```bash
  pytest --headed --slowmo 1000 -n 0
  ```
* Abrir el inspector/consola de Playwright (Trace Viewer en vivo) antes de que termine el test:
  Añade `page.pause()` en tu código Python, o si usas breakpoints interactivos:
  `breakpoint()`

**📊 Generar y Ver Reportes (Allure)**
* Generar el reporte en HTML (limpiando resultados anteriores):
  ```bash
  allure generate ./allure-results -o ./allure-report --clean
  ```
* Abrir el reporte en tu navegador web:
  ```bash
  allure open ./allure-report
  ```

**⚡ Pruebas de Rendimiento**
* **Con Locust (Local):** (Pruebas de carga sencillas en tu propia máquina exportando a CSV y HTML):
  ```bash
  locust -f tests/performance/locustfile.py --headless --host https://your-site.com --html reporte-locust.html
  ```
* **Con Locust (CI/CD o Avanzado):** (Ejecución paralela Master/Worker usando Docker Compose):
  ```bash
  export UID_GID=$(id -u):$(id -g)
  docker compose up --build --scale worker=3
  ```
* **Con Lighthouse** (Auditoría de rendimiento web):
  ```bash
  pytest --only-lighthouse -s
  ```

---

## 📁 Estructura del Proyecto

```
├── .agents/rules/          # Reglas y skills para AI assistants
├── .github/workflows/      # CI/CD con GitHub Actions
├── data/                   # Datos de prueba (credentials.json)
├── features/               # Archivos .feature (Gherkin/BDD)
├── poms/                   # Page Object Models
│   ├── base_page.py        # Clase base abstracta
│   └── create_business_page.py # POM de creación de negocio (Tarjetoso)
├── tests/
│   ├── e2e/                # Tests funcionales E2E
│   └── performance/        # Locust + Lighthouse
├── utils/                  # Utilidades compartidas
│   ├── api_testing.py      # Cliente API genérico
│   ├── email_reader.py     # Lector de OTP via IMAP
│   ├── lighthouse_utils.py # Runner de Lighthouse
│   └── screenshot_utils.py # Capturas automáticas en fallo
├── conftest.py             # Fixtures y hooks globales
├── pytest.ini              # Configuración centralizada de pytest
├── packages.txt            # Dependencias Python
└── docker-compose.yml      # Locust distribuido
```

---

## 👤 Autor
* **Jhonatan Flores** - [@jhonatan](https://github.com/Jhonatanfc94)

sudo systemctl start docker

Terminal 1 — Base de datos (una sola vez, se queda corriendo):
bash
cd spinjob-backend
sudo docker compose -f docker-compose.test.yml up -d

Terminal 2 — Backend apuntando a la DB de testing:
bash
cd spinjob-backend
ENV_FILE=.env.test uvicorn main:app --reload

Terminal 3 — Frontend (como siempre):
bash
cd spinjob-fronted
npm run dev

Terminal 4 — Ejecutar los tests:
bash
cd tarjetoso-tests
pytest tests/e2e/test_business_creation.py



pytest tests/e2e/namefile.py -v
pytest tests/e2e/namefile.py --headed --slowmo 1000 -v
locust -f tests/performance/locustfile.py --host http://localhost:5173 --headless --html artifacts/reporte_rendimiento.html



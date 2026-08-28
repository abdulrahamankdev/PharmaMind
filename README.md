# PharmaMind 🧬 
**Intelligent Drug Discovery Platform**

PharmaMind is an adversarial, evidence-grounded AI research assistant designed to accelerate pharmaceutical compound discovery. By combining advanced graph-based knowledge retrieval with a dual-agent LLM pipeline, PharmaMind generates, rigorously evaluates, and beautifully visualizes novel drug target hypotheses.

## ✨ Core Features
*   **Adversarial AI Engine**: Employs a dual-agent system. A `hypothesis_agent` synthesizes potential drug targets, while a `refuter_agent` aggressively cross-examines the hypothesis against ChEMBL evidence data to ensure scientific rigor.
*   **Knowledge Graph Visualization**: A high-performance, fully interactive **D3.js Target Network**. Features physics-based node clustering, sleek curved Bezier connections, and dynamic pathway highlighting on hover to trace complex disease-to-compound relationships.
*   **Degree-Penalized Scoring**: The integrated `scoring_service` calculates compound relevance using advanced algorithms that mitigate hub-node bias, ensuring accurate, high-confidence predictions.
*   **Enterprise-Grade UI/UX**: Built with a "Professional White" aesthetic, featuring glassmorphism shadows, modern `Outfit` typography, and rich, bouncy micro-animations across all dashboard icons and data tables.
*   **Robust Data Fallbacks**: Integrates directly with a Neo4j graph database, backed by an automated local CSV fallback engine to ensure the platform remains fully operational even when the primary database is offline.

## 🏗️ Technology Stack
*   **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.13)
*   **Frontend**: Vanilla HTML5, CSS3, JavaScript (No heavy framework dependencies)
*   **Data Visualization**: [D3.js](https://d3js.org/)
*   **Database**: Neo4j (Graph DB) + Local CSV engine
*   **Icons**: [Lucide Icons](https://lucide.dev/)
*   **AI Integration**: Local LLM connectivity (Configured for Qwen3.5)

## 🚀 Getting Started

### Prerequisites
Ensure you have Python 3.13 installed.

### Installation
1.  Clone the repository and navigate to the project root (`e:\PHARMA2\`).
2.  Install the required backend dependencies:
    ```bash
    pip install -r backend/requirements.txt
    ```
3.  Configure your environment variables in the `.env` file (e.g., Neo4j credentials, LLM model paths).

### Running the Application
PharmaMind is designed to serve its frontend directly through the FastAPI backend for seamless deployment.

1.  Start the FastAPI server:
    ```bash
    cd backend
    python main.py
    ```
2.  Open your web browser and navigate to the dashboard:
    **`http://127.0.0.1:8000/app/index.html`**

## 🎨 Design Philosophy
The user interface has been meticulously engineered for high-fidelity readability. We heavily prioritize high-contrast slate colors on a bright `#f8fafc` canvas. Every interactive element—from the sidebar navigation to the D3.js nodes—is equipped with cubic-bezier transition animations and rich drop-shadows to provide an incredibly tactile and premium user experience.

---
*Built for the future of computational pharmacology.*

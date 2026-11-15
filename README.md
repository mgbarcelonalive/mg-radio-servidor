---
title: MG Barcelona Live Radio Server
emoji: 🎧
colorFrom: purple
colorTo: pink
sdk: docker
app_port: 7860
pinned: true
---

# 🎧 MG Barcelona Live · Servidor de Radio en la Nube + Herramienta Web 24/7

Este paquete contiene **el Servidor de Radio 24/7 y la Herramienta de Estudio Web** de **MG Barcelona Live** listos para subir a un servidor gratuito en fase de prueba.

## ¿Qué incluye esta herramienta en el servidor?
1. **Emisión 24/7 desde el servidor (`/stream`)**: El propio servidor reproduce tus canciones y mezcla las cuñas oficiales de MG Barcelona Live automáticamente, aunque apagues tu ordenador.
2. **Herramienta Web de Control (`/panel`)**: Entras desde cualquier navegador (PC o móvil) para:
   - Subir canciones MP3 y cuñas directamente al servidor.
   - Ver cuántos oyentes hay conectados en vivo.
   - Cambiar de canción (`⏭ Siguiente`) o lanzar una cuña al instante (`🔊 Lanzar`).
   - Copiar el enlace fijo `/stream` para la web y la App móvil.

---

## 🚀 Cómo subirlo GRATIS a la nube (2 opciones sin coste)

### Opción A: Hugging Face Spaces (100% Gratis, sin tarjeta, 16 GB RAM y 50 GB de disco)
1. Crea una cuenta gratuita en [huggingface.co](https://huggingface.co/).
2. Pulsa en tu perfil → **New Space**.
3. Pon de nombre `mgbarcelonalive-radio`, elige **SDK: Docker** (Blank) y **Public**.
4. Sube todos los archivos de esta carpeta `SERVIDOR_NUBE` (`Dockerfile`, `servidor_nube.py`, `README.md` y la carpeta `cunas`).
5. En 2 minutos se encenderá solo y tendrás tu herramienta en vivo y tu stream fijo 24/7.

### Opción B: Render.com (Plan Free con Docker)
1. Crea una cuenta gratuita en [render.com](https://render.com/).
2. Pulsa **New + → Web Service** y selecciona **Deploy from Git repository** (o sube esta carpeta a un repositorio de tu GitHub).
3. En **Environment** elige **Docker** y en **Instance Type** selecciona **Free (0 $/mes)**.
4. Una vez desplegado, abre `https://tu-servidor.onrender.com/panel` (contraseña por defecto: `mg2026`).

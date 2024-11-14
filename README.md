# EraX-Address-Cleaner

---

## Requirements

Ensure you have the following installed and running:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Clone Repository

Clone this repository to your local machine:

```bash
git clone https://github.com/EraX-JS-Company/EraX-Address-Cleaner.git
```
## Start Service
1. **Navigate to the directory**
   ```bash
   cd EraX-Address-Cleaner
   ```
2. **Create key.pem, cert.pem (self-signed certificate)**
   ```bash
   mkdir openssl
   cd openssl
   openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 3650
   cd ..
   ```

3. **Create dotenv file**
    ```bash
   touch .env
   nano .env
   ```
   - Create 2 variables: GEMINI_KEY, TOKENS
   ```bash
    GEMINI_KEY=<Gemini API KEY>
    TOKENS=<TOKEN_0>,<TOKEN_1>
   ```
   - Save dotenv file

4. **Start with Docker Compose**
   ```bash
    docker compose up -d --build
   ```


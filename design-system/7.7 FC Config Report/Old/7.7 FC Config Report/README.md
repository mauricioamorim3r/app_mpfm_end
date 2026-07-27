# Flow Computer Configuration Analisys

Scaffold inicial da `Release 1` da plataforma Bacalhau.

## Estrutura

- `backend/`: API local FastAPI, banco SQLite, ingestão e parsers iniciais
- `frontend/`: interface React + Vite com o código-fonte e o build compilado em `dist/`
- `docs/`: PRD e plano de implementação
- `install_sgmed.ps1`: instalação das dependências Python no usuário atual
- `start_sgmed.ps1`: inicialização local do pacote via Python

## Uso no PC de destino

O pacote distribuído pode ser executado apenas com `Python`, sem instalar `Node.js`, porque o frontend já vai compilado em `frontend/dist` e é servido pelo próprio FastAPI.

Não é necessário, nem esperado, criar ambiente virtual.

## Requisito de Python

Use preferencialmente `Python 3.14`.

O pacote foi validado neste ambiente com `Python 3.14`. Se o computador tiver outras versões instaladas, prefira instalar e executar com `py -3.14`.

### Instalação

```powershell
cd C:\ConfiguraCV
py -3.14 -m pip install --user -r backend\requirements.txt
```

ou:

```powershell
cd C:\ConfiguraCV
python -m pip install --user -r backend\requirements.txt
```

Se quiser, você também pode usar:

```powershell
cd C:\ConfiguraCV
.\install_sgmed.ps1
```

### Execução

Opção 1:

```powershell
cd C:\ConfiguraCV
.\start_sgmed.ps1
```

O script escolhe automaticamente uma porta livre, começando em `8010`, e mostra a URL correta no próprio terminal.

Opção 2:

```powershell
cd C:\ConfiguraCV
py -3.14 -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --app-dir backend
```

ou:

```powershell
cd C:\ConfiguraCV
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --app-dir backend
```

Depois, abra:

```text
http://127.0.0.1:8010
```

## Desenvolvimento do frontend

Só é necessário `Node.js` se você quiser alterar a interface e recompilar o frontend.

```powershell
cd C:\ConfiguraCV\frontend
npm install
npm run dev
```

ou para gerar novo build:

```powershell
cd C:\ConfiguraCV\frontend
npm install
npm run build
```

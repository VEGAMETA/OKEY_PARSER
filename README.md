# OKEY_PARSER

Parser for https://www.okeydostavka.ru/

Parser is using proxies. Just put proxies.txt
(with format of ip:port:user:pass) into the root directory.

Outputs csv file, by parsing categories with exact address location
(filename, categories and address named in config.py)

## Installation

```cmd
git clone https://github.com/VEGAMETA/OKEY_PARSER.git
cd OKEY_PARSER
python -m venv venv
```

#### Windows

```cmd
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

#### Linux

```bash
source venv/bin/activate
pip install -r requirements.txt
python main.py
```


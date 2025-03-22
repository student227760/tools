#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Jupyter Notebook Markdownセル・コードセル 自動翻訳スクリプト

ディレクトリ内のJupyter Notebook（.ipynb）ファイルのMarkdownセルを自動で日本語に翻訳し、
新たに翻訳済みファイル（jp_ファイル名.ipynb）を作成します。

翻訳エンジンは、以下の2種類から選択可能です:
- googletrans (非公式Google翻訳APIライブラリ)
- Google Cloud Translation API (公式)

【主な機能】
- ディレクトリ内の.ipynbファイルを一括処理
- Markdownセルを日本語に翻訳
- オプションで、コードセル内の文字列リテラル（20文字以上）も翻訳
- 翻訳エンジンを柔軟に切り替え可能（--engine オプション）
- Typer を用いたモダンなCLI

【使い方】
--------------------------------------------------
1. 必要なライブラリをインストール
   pip install googletrans==4.0.0-rc1 google-cloud-translate==3.11.2 typer[all]

2. Google Cloud Translation API を利用する場合は、サービスアカウントの認証情報を使用してください。
   サービスアカウントキーのJSONファイルを取得し、環境変数 GOOGLE_APPLICATION_CREDENTIALS にそのファイルパスを設定します。
   (例: export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account.json")

3. 実行例
   # googletrans を使う場合（コードセルは翻訳しない）
   python translate_notebooks.py --directory /path/to/notebook-directory --engine googletrans

   # gcloud を使い、コードセル内の文字列リテラルも翻訳する場合
   python translate_notebooks.py --directory /path/to/notebook-directory --engine gcloud --translate-code
--------------------------------------------------
"""

import os
import json
import time
import logging
import re
from typing import Optional
from abc import ABC, abstractmethod
import typer

# ----------------------------------------
# ログ設定
# ----------------------------------------
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ----------------------------------------
# 翻訳エンジンインターフェース
# ----------------------------------------
class TranslatorInterface(ABC):
    @abstractmethod
    def translate(self, text: str, target_lang: str = 'ja') -> str:
        """テキストを指定言語に翻訳する"""
        pass

# ----------------------------------------
# googletrans 実装
# ----------------------------------------
class GoogletransTranslator(TranslatorInterface):
    def __init__(self, retries: int = 3, delay: int = 2):
        from googletrans import Translator
        self.translator = Translator()
        self.retries = retries
        self.delay = delay

    def translate(self, text: str, target_lang: str = 'ja') -> str:
        if not text.strip():
            return text

        for attempt in range(1, self.retries + 1):
            try:
                result = self.translator.translate(text, dest=target_lang)
                if result and result.text:
                    logger.debug(f"[googletrans] Success on attempt {attempt}")
                    return result.text
            except Exception as e:
                logger.warning(f"[googletrans] Attempt {attempt}/{self.retries} failed: {e}")
                time.sleep(self.delay)
        logger.error("[googletrans] Translation failed after retries")
        return text

# ----------------------------------------
# Google Cloud Translation API 実装 (using service account credentials)
# ----------------------------------------
class GoogleCloudTranslator(TranslatorInterface):
    def __init__(self):
        from google.cloud import translate_v2 as translate
        # Check for service account credentials
        credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path:
            logger.error("Environment variable 'GOOGLE_APPLICATION_CREDENTIALS' is not set. "
                         "Please set it to the path of your service account JSON file.")
            raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS not set. "
                                   "See https://cloud.google.com/docs/authentication/getting-started for more details.")
        self.client = translate.Client()

    def translate(self, text: str, target_lang: str = 'ja') -> str:
        if not text.strip():
            return text
        try:
            result = self.client.translate(text, target_language=target_lang)
            logger.debug("[gcloud] Translation success")
            return result['translatedText']
        except Exception as e:
            logger.error(f"[gcloud] Translation failed: {e}")
            return text

# get_translator returns a TranslatorInterface based on the engine string
def get_translator(engine: str) -> TranslatorInterface:
    if engine == 'googletrans':
        return GoogletransTranslator()
    elif engine == 'gcloud':
        return GoogleCloudTranslator()
    else:
        raise ValueError(f"Unsupported engine: {engine}")

# ----------------------------------------
# コードセル内の文字列リテラル翻訳（正規表現ベース）
# ----------------------------------------
STRING_LITERAL_RE = re.compile(r"(?P<quote>['\"]{1,3})(?P<content>.*?)(?P=quote)", re.DOTALL)

def translate_code_cell_source(source: list[str], translator: TranslatorInterface, min_length: int = 20) -> list[str]:
    """
    コードセルのソースから文字列リテラルを検出し、
    20文字以上の場合に翻訳する。
    """
    code_text = "".join(source)
    
    def replacer(match: re.Match) -> str:
        quote = match.group("quote")
        content = match.group("content")
        if len(content) >= min_length:
            translated = translator.translate(content)
            logger.debug(f"[code] Translated literal: {content[:20]}... -> {translated[:20]}...")
            return f"{quote}{translated}{quote}"
        else:
            return match.group(0)
    
    new_code_text = STRING_LITERAL_RE.sub(replacer, code_text)
    return new_code_text.splitlines(keepends=True)

# ----------------------------------------
# Notebookのセル翻訳処理（Markdown＋オプションでコードセル）
# ----------------------------------------
def translate_notebook_cells(input_path: str, translator: TranslatorInterface, translate_code: bool = False, output_path: Optional[str] = None) -> None:
    logger.info(f"Loading notebook: {input_path}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read notebook: {e}")
        return

    translated_any = False
    for cell in notebook.get('cells', []):
        cell_type = cell.get('cell_type')
        if cell_type == 'markdown':
            original_text = ''.join(cell.get('source', []))
            translated_text = translator.translate(original_text)
            if translated_text != original_text:
                translated_any = True
                cell['source'] = [translated_text]
        elif cell_type == 'code' and translate_code:
            original_source = cell.get('source', [])
            new_source = translate_code_cell_source(original_source, translator, min_length=20)
            if "".join(new_source) != "".join(original_source):
                translated_any = True
                cell['source'] = new_source

    if not output_path:
        dirname, filename = os.path.split(input_path)
        output_path = os.path.join(dirname, f"jp_{filename}")

    if translated_any:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(notebook, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved translated notebook: {output_path}")
        except Exception as e:
            logger.error(f"Failed to save translated notebook: {e}")
    else:
        logger.info(f"No cells were translated in {input_path}")

def translate_notebooks_in_directory(directory: str, translator: TranslatorInterface, translate_code: bool = False) -> None:
    if not os.path.isdir(directory):
        logger.error(f"Directory not found: {directory}")
        return

    logger.info(f"Translating notebooks in directory: {directory}")
    for filename in os.listdir(directory):
        if filename.endswith('.ipynb'):
            input_path = os.path.join(directory, filename)
            translate_notebook_cells(input_path, translator, translate_code)

# ----------------------------------------
# Typer CLI エントリポイント
# ----------------------------------------
app = typer.Typer()

@app.command()
def main(
    directory: str = typer.Option(..., help="対象となるディレクトリのパス（.ipynbファイルを含む）"),
    engine: str = typer.Option('googletrans', help="翻訳エンジン ('googletrans' または 'gcloud')"),
    translate_code: bool = typer.Option(False, help="コードセル内の文字列リテラル（20文字以上）も翻訳する場合は True")
) -> None:
    """
    指定したディレクトリ内のJupyter NotebookのMarkdownセルを日本語に翻訳します。
    オプションで、コードセル内の文字列リテラル（20文字以上）の翻訳も可能です。
    """
    allowed_engines = ['googletrans', 'gcloud']
    if engine not in allowed_engines:
        raise typer.BadParameter(f"Engine must be one of {allowed_engines}")
    translator = get_translator(engine)
    translate_notebooks_in_directory(directory, translator, translate_code)

if __name__ == "__main__":
    app()

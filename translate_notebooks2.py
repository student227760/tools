#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Jupyter Notebook Markdownセル 自動翻訳スクリプト

ディレクトリ内のJupyter Notebook（.ipynb）ファイルのMarkdownセルを自動で日本語に翻訳し、
新たに翻訳済みファイル（translated_ファイル名.ipynb）を作成します。

翻訳エンジンは、以下の2種類から選択可能です:
- googletrans (非公式Google翻訳APIライブラリ)
- Google Cloud Translation API (公式)

【主な機能】
- ディレクトリ内の.ipynbファイルを一括処理
- Markdownセルのみ日本語に翻訳
- 翻訳エンジンを柔軟に切り替え可能（--engine オプション）

【使い方】
--------------------------------------------------
1. 必要なライブラリをインストール
   pip install googletrans==4.0.0-rc1 google-cloud-translate==3.11.2 typer[all]

2. Google Cloud Translation API を利用する場合は、環境変数にAPIキーを設定
   export GOOGLE_API_KEY="あなたのAPIキー"

3. 実行例
   # googletrans を使う場合
   python translate_notebooks.py --directory /path/to/notebook-directory --engine googletrans

   # Google Cloud Translation API を使う場合
   python translate_notebooks.py --directory /path/to/notebook-directory --engine gcloud
--------------------------------------------------
"""

import os
import json
import time
import logging
from typing import Optional, Literal
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
# Google Cloud Translation API 実装
# ----------------------------------------
class GoogleCloudTranslator(TranslatorInterface):
    def __init__(self):
        from google.cloud import translate_v2 as translate
        api_key = os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            logger.error("環境変数 'GOOGLE_API_KEY' が設定されていません。")
            raise EnvironmentError("GOOGLE_API_KEY not set")
        self.client = translate.Client(api_key=api_key)

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

# 型エイリアス: 翻訳エンジンの種類
EngineType = Literal['googletrans', 'gcloud']

def get_translator(engine: EngineType) -> TranslatorInterface:
    if engine == 'googletrans':
        return GoogletransTranslator()
    elif engine == 'gcloud':
        return GoogleCloudTranslator()
    else:
        raise ValueError(f"Unsupported engine: {engine}")

# ----------------------------------------
# NotebookのMarkdownセル翻訳処理
# ----------------------------------------
def translate_markdown_cells(input_path: str, translator: TranslatorInterface, output_path: Optional[str] = None) -> None:
    logger.info(f"Loading notebook: {input_path}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read notebook: {e}")
        return

    translated_any = False
    for cell in notebook.get('cells', []):
        if cell.get('cell_type') == 'markdown':
            original_text = ''.join(cell.get('source', []))
            translated_text = translator.translate(original_text)
            if translated_text != original_text:
                translated_any = True
                cell['source'] = [translated_text]

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
        logger.info(f"No markdown cells translated in {input_path}")

def translate_notebooks_in_directory(directory: str, translator: TranslatorInterface) -> None:
    if not os.path.isdir(directory):
        logger.error(f"Directory not found: {directory}")
        return

    logger.info(f"Translating notebooks in directory: {directory}")
    for filename in os.listdir(directory):
        if filename.endswith('.ipynb'):
            input_path = os.path.join(directory, filename)
            translate_markdown_cells(input_path, translator)

# ----------------------------------------
# Typer CLI エントリポイント
# ----------------------------------------
app = typer.Typer()

@app.command()
def main(
    directory: str = typer.Option(..., help="ディレクトリ内の.ipynbファイルを対象とするパス"),
    engine: EngineType = typer.Option('googletrans', help="翻訳エンジン ('googletrans' または 'gcloud')")
) -> None:
    """
    指定したディレクトリ内のJupyter NotebookのMarkdownセルを日本語に翻訳します。
    """
    translator = get_translator(engine)
    translate_notebooks_in_directory(directory, translator)

if __name__ == "__main__":
    app()

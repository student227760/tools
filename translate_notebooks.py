#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Jupyter Notebook Markdownセル 自動翻訳スクリプト

指定したディレクトリ内にあるすべてのJupyter Notebook（.ipynb）ファイルのMarkdownセルを自動で日本語に翻訳し、新たに翻訳済みファイルを作成する

【主な機能】
- ディレクトリ内の.ipynbファイルを一括処理
- 各ノートブックのMarkdownセルを日本語へ翻訳
- 'translated_ファイル名.ipynb' として保存（元ファイルは上書きしない）
- Google翻訳API（googletransライブラリ）を使用
- リトライ・エラーハンドリング

【使い方】
--------------------------------------------------
1. 必要なライブラリをインストール
   pip install googletrans==4.0.0-rc1

2. 実行コマンド
   python translate_notebooks.py /path/to/notebook-directory

3. 実行後、翻訳されたノートブックが
   'translated_ファイル名.ipynb' として保存される
--------------------------------------------------

"""

import os
import json
import time
import logging
from typing import Optional
from googletrans import Translator

# ----------------------------------------
# ログの設定
# ----------------------------------------
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def translate_text(
    text: str,
    translator: Translator,
    retries: int = 3,
    delay: int = 2
) -> str:
    """
    テキストを日本語に翻訳する（失敗時リトライ処理付き）

    Parameters:
        text (str): 翻訳対象のテキスト
        translator (Translator): googletransの翻訳インスタンス
        retries (int): 最大リトライ回数
        delay (int): リトライ間の待機時間（秒）

    Returns:
        str: 翻訳後の日本語テキスト（失敗時は原文を返す）
    """
    if not text.strip():
        return text

    for attempt in range(1, retries + 1):
        try:
            result = translator.translate(text, dest='ja')
            if result and result.text:
                logger.debug(f"Translation successful on attempt {attempt}")
                return result.text
        except Exception as e:
            logger.warning(f"Attempt {attempt}/{retries} failed: {e}")
            time.sleep(delay)

    logger.error("Translation failed after retries. Returning original text.")
    return text

def translate_markdown_cells(
    input_path: str,
    output_path: Optional[str] = None
) -> None:
    """
    単一のJupyter Notebookファイルを読み込み、Markdownセルを翻訳する

    Parameters:
        input_path (str): 翻訳元の.ipynbファイルパス
        output_path (Optional[str]): 翻訳結果を保存するファイルパス（未指定なら自動生成）
    """
    translator = Translator()

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
            logger.debug(f"Original markdown: {original_text[:50]}...")
            translated_text = translate_text(original_text, translator)

            if translated_text != original_text:
                translated_any = True
                logger.debug(f"Translated markdown: {translated_text[:50]}...")

            cell['source'] = [translated_text]

    if not output_path:
        dirname, filename = os.path.split(input_path)
        output_path = os.path.join(dirname, f"translated_{filename}")

    if translated_any:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(notebook, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved translated notebook: {output_path}")
        except Exception as e:
            logger.error(f"Failed to save translated notebook: {e}")
    else:
        logger.info(f"No markdown cells were translated in {input_path}.")

def translate_notebooks_in_directory(directory: str) -> None:
    """
    指定ディレクトリ内の全ての.ipynbファイルを翻訳対象とする

    Parameters:
        directory (str): 処理対象となるディレクトリのパス
    """
    if not os.path.isdir(directory):
        logger.error(f"Directory not found: {directory}")
        return

    logger.info(f"Translating notebooks in directory: {directory}")
    for filename in os.listdir(directory):
        if filename.endswith('.ipynb'):
            input_path = os.path.join(directory, filename)
            translate_markdown_cells(input_path)

# ----------------------------------------
# CLIエントリポイント
# ----------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Translate Markdown cells in Jupyter notebooks to Japanese."
    )
    parser.add_argument(
        'directory',
        type=str,
        help='Directory containing .ipynb files to translate'
    )
    args = parser.parse_args()

    translate_notebooks_in_directory(args.directory)

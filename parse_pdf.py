from os import listdir
from os.path import isfile, join
import os
import re
import json
import time
import base64
import tkinter as tk
import pandas as pd
import argparse
import openai
from openai import (
    OpenAI,
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    InternalServerError,
)
from pdf2image import convert_from_path
from annotate_images import ImageCropper
# from utils import parse_gpt_output


# pre_prompt = """Please extract the multiple-choice questions in the attached image {} language in which they appear. There can be one or multiple questions per page. The question number should be inside the <question_num></question_num> tags, the question should be inside the tags  <question> </question> and the choices inside the tags <choices> </choices>. If the questions do not have choices do not include that question. Also, determine the category of question from the following - physics, chemistry, agriculture, medical, maths, biology, reasoning, numerical ability, scientific aptitude, general knowledge, english language, drawing aptitude, computer concepts and pharmacy. Like if it belongs to chemistry output <category>chemistry</category> if english language output <category>english language</category>. If the question requires some image or a figure to arrive at an answer respond with <image>yes</image> else respond with <image>no</image>. If a particular question requires referring to a passage, respond with <context>yes</context> else respond  with <context>no</context>. Additionally, the correct answer might be present in the image either explicitly provided or by a mark next to the correct answer of the multiple choices. Provide the number or letter of the correct answer between the tags <answer> </answer>. If no answer is present, leave empty.
# The output format should be the following, depending on the number of choices present:
# <question> </question>
# <choices>
# </choices>
# <answer> </answer>
# <image></image>
# <context></context>
# <category></category>
# """
pre_prompt = """
Extract all the text in {} from the attached image. The image consists of multiple choice questions in {}. The question always begins after numbers (like Q.1 , Q.2 , Q.10 and so on). The multiple choice options always start with (A) , (B) , (C) or (D). Extract everything as mentioned above as follows.

The question number should be inside the <question_num></question_num> tags. If the instructions span multiple questions repeat it for each question. The question text should be inside the <question> </question> tags. The choices inside the tags <choices> </choices>. Also, determine the category of question from the following - physics, chemistry, maths, biology, mental ability, reasoning. Like if it belongs to chemistry output <category>chemistry</category> if maths output <category>maths</category>. If the question requires some image or a figure to arrive at an answer respond with <image>yes</image> else respond with <image>no</image>. If a particular question requires directions or referring to a passage, respond with <context>yes</context> else respond  with <context>no</context>.
The output format should be the following, depending on the number of choices present:

<question_num></question_num>
<question> </question>
<choices> 

</choices>
<image></image>
<context></context>
<category></category>

"""

# pre_prompt = """
# Extract all the text in {} from the attached image. The image consists of multiple choice questions in English and {}. The question always begins after question numbers (like 1. , 2. , 3. and so on). For some questions there are instructions associated with it that always begins AFTER a phrase like "Direction Questions (<question_start> - <question_end>) <instruction>" for example, "Direction Questions (9-12) Find the odd one out from the given alternatives" meaning instructions for all questions from 9 to 12". Extract those instructions in {} language and include that with every associated question. The multiple choice options always start with (1) , (2) , (3) or (4). Extract everything as mentioned above as follows.

# The question number should be inside the <question_num></question_num> tags. The instructions for questions should be inside the <instruction></instruction> tag. If the instructions span multiple questions repeat it for each question. The question text should be inside the <question> </question> tags. The choices inside the tags <choices> </choices>. Also, determine the category of question from the following - physics, chemistry, maths, biology, mental ability, reasoning. Like if it belongs to chemistry output <category>chemistry</category> if english language output <category>english language</category>. If the question requires some image or a figure to arrive at an answer respond with <image>yes</image> else respond with <image>no</image>. If a particular question requires directions or referring to a passage, respond with <context>yes</context> else respond  with <context>no</context>.
# The output format should be the following, depending on the number of choices present:

# <question_num></question_num>
# <instruction></instruction>
# <question> </question>
# <choices> 

# </choices>
# <image></image>
# <context></context>
# <category></category>

# """


def get_options(choices_matches):
    option_pattern = r"\n\(([A-Z])\) ([^\n]+)"
    final_matches = []
    for choice_match in choices_matches:
        options = re.findall(option_pattern, choice_match)
        final_matches.append([option[1] for option in options])
    return final_matches


def get_options_2(choices_matches):
    option_pattern = r"\n\(\d+\) ([^\n]+)"
    final_matches = []
    for choice_match in choices_matches:
        options = re.findall(option_pattern, choice_match)
        final_matches.append(options)
    return final_matches


def get_options_3(choices_matches):
    option_pattern = r"\d+\) ([^\n]+)"
    final_matches = []
    for choice_match in choices_matches:
        options = re.findall(option_pattern, choice_match)
        final_matches.append(options)
    return final_matches
def get_options_4(choices_matches):
    option_pattern = r"\(\d+\)\s*([^\n]+)"
    final_matches = []
    for choice_match in choices_matches:
        options = re.findall(option_pattern, choice_match)
        final_matches.append(options)
    return final_matches
def get_options_5(choices_matches):
    option_pattern = r"\([a-z]\)\s*([^\n]+)"
    final_matches = []
    for choice_match in choices_matches:
        options = re.findall(option_pattern, choice_match)
        final_matches.append(options)
    return final_matches



def parse_gpt_output(response, pdf_path):
    question_pattern = re.compile(r"<question>(.*?)</question>", re.DOTALL)
    instruction_pattern = re.compile(r"<instruction>(.*?)</instruction>", re.DOTALL)
    choices_pattern = re.compile(r"<choices>(.*?)</choices>", re.DOTALL)
    answer_pattern = re.compile(r"<answer>(.*?)</answer>", re.DOTALL)
    requires_image_pattern = re.compile(r"<image>(.*?)</image>", re.DOTALL)
    category_pattern = re.compile(r"<category>(.*?)</category>", re.DOTALL)
    context_pattern = re.compile(r"<context>(.*?)</context>", re.DOTALL)
    question_num = re.compile(r"<question_num>(.*?)</question_num>", re.DOTALL)

    # Find all matches for questions
    question_matches = question_pattern.findall(response)
    instruction_matches = instruction_pattern.findall(response)
    choices_matches = choices_pattern.findall(response)
    requires_image = requires_image_pattern.findall(response)
    contexts = context_pattern.findall(response)
    categories = category_pattern.findall(response)
    q_nums = question_num.findall(response)
    if len(instruction_matches) == len(question_matches):
        for i in range(len(question_matches)):
            question_matches[i] = instruction_matches[i] + "\n" + question_matches[i]
    else:
        if len(instruction_matches) < len(question_matches):
            instruction_matches += [''] * (len(question_matches) - len(instruction_matches))
        else:
            raise ValueError()

    if "UP-CET" in pdf_path:
        option_pattern = r"\n\(([A-Z])\) ([^\n]+)"
        final_matches = []
        for choice_match in choices_matches:
            options = re.findall(option_pattern, choice_match)
            final_matches.append([option[1] for option in options])
    elif "Karnataka" in pdf_path:
        final_matches = get_options_3(choices_matches)
    elif "malayalam" in pdf_path:
        final_matches = get_options_4(choices_matches)
    elif "Urdu" in pdf_path:
        final_matches = get_options_5(choices_matches)
    else:
        final_matches = get_options(choices_matches)

    answer_matches = answer_pattern.findall(response)
    return (
        question_matches,
        final_matches,
        requires_image,
        categories,
        contexts,
        q_nums,
    )


def chat_completion(
    client,
    messages,
    model,
    return_text=True,
    return_usage=True,
    model_args=None,
):
    """
    Calls openai API with the image and the prompt

    :param client: OpenAI client
    :param messages: list, array of messages
    :param model: str
    :param return_text: bool
    :param return_usage: bool
    :param model_args:
    return: dict
    """
    if model_args is None:
        model_args = {}

    while True:
        try:
            response = client.chat.completions.create(
                model=model, messages=messages, **model_args
            )
            text = response.choices[0].message.content.strip()
            usage = response.usage

            if return_text and return_usage:
                return text, dict(usage)

            if return_text:
                return text

            if return_usage:
                return usage

            return response
        except (
            APITimeoutError,
            APIConnectionError,
            RateLimitError,
            InternalServerError,
        ) as e:
            print(f"OpenAI error: {str(e)}. Waiting for 1 minute.")
            time.sleep(60)
            continue


def encode_image(image_path):
    """
    Function to encode the image
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def main(pdf_path, openai_key, language, page_start=0, page_end=9999, source=""):
    """
    It performs the main text extraction pipeline of the script.

    :param dir_path: str
    :param openai_key: str
    """
    # create client with openai credentials
    client = OpenAI(api_key=openai_key)

    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

    # Define paths for 'imgs' and 'results' folders
    parent_directory = os.path.dirname(os.path.dirname(pdf_path))
    imgs_folder = os.path.join(parent_directory, "imgs", pdf_name)
    result_path = os.path.join(parent_directory, "results")
    crops_path = os.path.join(parent_directory, "crops")
    # Create directories if they don't exist
    os.makedirs(imgs_folder, exist_ok=True)
    os.makedirs(result_path, exist_ok=True)
    os.makedirs(crops_path, exist_ok=True)
    images = convert_from_path(pdf_path, first_page=1)
    images = images[page_start:page_end]
    page_num = page_start + 1

    # Step 2: Preprocess the image (deskew)
    results = list()
    q_idx = 0
    for _, image in enumerate(images):
        print("Processing page: {}".format(page_num))
        image_path = os.path.join(imgs_folder, f"page_{page_num+1}.png")
        image.save(image_path, "PNG")
        base64_image = encode_image(image_path)

        # Step 3: Pass img to gpt-4 for mcq extraction
        try:
            message = [
                {
                    "type": "text",
                    "text": pre_prompt.format(language, language, language),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ]
            response, _ = chat_completion(
                client,
                [{"role": "user", "content": message}],
                model="gpt-4o",
                return_text=True,
                return_usage=True,
                model_args={
                    "temperature": 0.0,
                    "max_tokens": 4096,
                    "top_p": 1,
                    "frequency_penalty": 0,
                    "presence_penalty": 0,
                },
            )
            # Step 4: Process gpt-4 output
            (
                questions,
                choices,
                requires_image,
                categories,
                contexts,
                q_nums,
            ) = parse_gpt_output(response, pdf_path)
            page_results = []
            if not all(
                len(lst) == len(questions)
                for lst in [
                    choices,
                    requires_image,
                    categories,
                    contexts,
                    q_nums,
                ]
            ):
                print("Skipped page", page_num)
            else:
                for question, options, has_image, category, cntx, q_num in zip(
                    questions,
                    choices,
                    requires_image,
                    categories,
                    contexts,
                    q_nums,
                ):
                    new_row = {
                        "language": language,
                        "country": "India",
                        "file_name": pdf_name,
                        "source": source,
                        "license": "",  # check
                        "level": "high school",
                        "category_en": category,
                        "category_original_lang": None,
                        "region_related": False,
                        "original_question_idx": q_num,
                        "page_num": page_num,
                        "response": response,
                        "question": question,
                        "options": options,
                        "answer": "",
                        "requires_image": has_image,
                        "context": cntx,
                    }
                    page_results.append(new_row)
                    q_idx += 1
            # os.makedirs(pdf_crops_path, exist_ok=True)
            output_file = os.path.join(result_path,  f"{pdf_name}_page_{page_num+1}.json")
            root = tk.Tk()
            pdf_crops_path = os.path.join(crops_path, f"{pdf_name}_page_{page_num+1}")
            app = ImageCropper(root, image_path, pdf_crops_path, new_row)
            root.mainloop()
            page_num += 1
            # Save the results to a JSON file
            with open(output_file, "w", encoding="utf-8") as json_file:
                json.dump(page_results, json_file, indent=4, ensure_ascii=False)
            print("Data saved: {}".format(output_file))

        except openai.BadRequestError:
            pass
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--pdf_path", type=str, help="Path to the PDF file.")
    parser.add_argument(
        "-l",
        "--lang",
        type=str,
        default="english",
        help="Language(s) for the PDF",
    )
    parser.add_argument("--source", type=str, default="", help="Link to PDF")
    parser.add_argument(
        "--pages",
        type=int,
        default=1000,
        help="Maximum number of pages to process (default: 1000).",
    )
    parser.add_argument(
        "--page_start",
        type=int,
        default=8,
        help="Start page.",
    )
    parser.add_argument(
        "--page_end",
        type=int,
        default=18,
        help="End page.",
    )
    parser.add_argument(
        "-k",
        "--key",
        help="OpenAI API Key",
        default="",
    )

    args = parser.parse_args()
    main(
        pdf_path=args.pdf_path,
        openai_key=args.key,
        language=args.lang,
        # pages=args.pages,
        page_start=args.page_start,
        page_end=args.page_end,
        source=args.source,
    )
# python parse_pdf.py --pdf_path ./exams/JEE_Adv/2024/Papers/JEEAdv2024_Paper2_Hindi.pdf --lang Hindi --source https://jeeadv.ac.in/documents/JEEAdv2024_Paper2_Hindi.pdf --pages 10

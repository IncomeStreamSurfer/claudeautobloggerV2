import os
from dotenv import load_dotenv
import anthropic
import signal
import sys
import threading
import keyboard

# Setup KeyboardInterrupt handling
def signal_handler(signal, frame):
    print("Interrupt received, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Load variables from .env file
load_dotenv()

# Get variables from environment
brand_name = os.getenv("BRAND_NAME")
keywords_file_path = os.getenv("KEYWORDS_FILE_PATH")
sample_article_file_path = os.getenv("SAMPLE_ARTICLE_FILE_PATH")
pages_file_path = os.getenv("PAGES_FILE_PATH")
products_file_path = os.getenv("PRODUCTS_FILE_PATH")
blogs_file_path = os.getenv("BLOGS_FILE_PATH")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
use_perplexity = os.getenv("USE_PERPLEXITY", "false").lower() == "true"
content_type = os.getenv("CONTENT_TYPE", "article")
business_type = os.getenv("BUSINESS_TYPE", "")
article_framing = os.getenv("ARTICLE_FRAMING", "")
brand_guidelines_file_path = os.getenv("BRAND_GUIDELINES_FILE_PATH")
brand_images_file_path = os.getenv("BRAND_IMAGES_FILE_PATH")
article_tone = os.getenv("ARTICLE_TONE", "")
famous_person = os.getenv("FAMOUS_PERSON", "")

# Read file contents
def read_file_content(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()

keywords = read_file_content(keywords_file_path).splitlines()
sample_article = read_file_content(sample_article_file_path)
pages = read_file_content(pages_file_path)
products = read_file_content(products_file_path)
blogs = read_file_content(blogs_file_path)
brand_guidelines = read_file_content(brand_guidelines_file_path)
brand_images = read_file_content(brand_images_file_path)

def get_user_input(prompt):
    global user_input
    user_input = input(prompt)

def stream_content(stream):
    content = ""
    for text in stream.text_stream:
        print(text, end="", flush=True)
        content += text
        if keyboard.is_pressed('p'):
            print("\nPaused. Press 'c' to continue or 'f' to provide feedback.")
            while True:
                if keyboard.is_pressed('c'):
                    print("\nResuming...")
                    break
                elif keyboard.is_pressed('f'):
                    raise KeyboardInterrupt
    return content

def select_relevant_content(keyword, content_type, pages, products, blogs, brand_images, api_key):
    client = anthropic.Client(api_key=api_key)
    system_prompt = f"""
    You are an AI assistant tasked with selecting relevant content for a {content_type} about the keyword "{keyword}".
    From the provided pages, products, blogs, and brand images, choose the most relevant ones that would be suitable for creating an engaging and informative {content_type}.
    Please select images and product links, or any type of links/images that are strictly relevant to the blog post. For example for an article about  black sneakers, please only choose black sneakers.
    Return the selected content in the following format:
    Pages:
    <selected pages, one per line>

    Products:
    <selected products, one per line, in the format "Title: <title>, URL: <url>">

    Blogs:
    <selected blogs, one per line>

    Brand Images:
    <selected brand images, one per line, in the format "Image: <title>, URL: <url>">
    """
    user_prompt = f"""
    Keyword: {keyword}
    Content Type: {content_type}

    Pages:
    {pages}

    Products:
    {products}

    Blogs:
    {blogs}

    Brand Images:
    {brand_images}
    """
    while True:
        try:
            print("Selecting relevant content...")
            print("Press 'p' to pause the selection process.")
            with client.messages.stream(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            ) as stream:
                content = stream_content(stream)
        except KeyboardInterrupt:
            print("\nSelection paused.")
            feedback = input("Please provide your feedback (or press Enter to continue): ")
            if feedback.strip() == "":
                break
            else:
                print("Feedback received. Restarting the selection with the updated prompt.")
                user_prompt += f"\nUser Feedback: {feedback}"
        else:
            print("\nContent selection completed.")
            break

    return content

def generate_content(system_prompt, user_prompt, api_key):
    client = anthropic.Client(api_key=api_key)
    while True:
        try:
            print("Generating content...")
            print("Press 'p' to pause the generation process.")
            with client.messages.stream(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            ) as stream:
                content = stream_content(stream)
        except KeyboardInterrupt:
            print("\nGeneration paused.")
            feedback = input("Please provide your feedback (or press Enter to continue): ")
            if feedback.strip() == "":
                break
            else:
                print("Feedback received. Restarting the generation with the updated prompt.")
                user_prompt += f"\nUser Feedback: {feedback}"
        else:
            print("\nContent generation completed.")
            break
    return content

def parse_content(content):
    sections = content.split("\n\n")
    parsed_content = {}
    for section in sections:
        lines = section.strip().split("\n")
        if lines:
            section_name = lines[0].strip(":")
            if section_name == "Products" or section_name == "Brand Images":
                parsed_content[section_name] = []
                for line in lines[1:]:
                    if "Title:" in line and ", URL:" in line:
                        title, url = line.split("Title:")[1].split(", URL:")
                        parsed_content[section_name].append({"title": title.strip(), "url": url.strip()})
                    else:
                        parsed_content[section_name].append({"title": line.strip(), "url": ""})
            else:
                parsed_content[section_name] = lines[1:]
    return parsed_content

if __name__ == "__main__":
    for keyword in keywords:
        relevant_content = select_relevant_content(
            keyword, content_type, 
            pages=read_file_content(pages_file_path), 
            products=read_file_content(products_file_path), 
            blogs=read_file_content(blogs_file_path), 
            brand_images=read_file_content(brand_images_file_path),
            api_key=anthropic_api_key
        )

        if relevant_content:
            parsed_content = parse_content(relevant_content)
            formatted_products = "\n".join([f"Title: {p['title']}, URL: {p['url']}" for p in parsed_content.get('Products', [])])
            formatted_pages = "\n".join(parsed_content.get('Pages', []))
            formatted_blogs = "\n".join(parsed_content.get('Blogs', []))
            formatted_images = "\n".join([f"Image: {img['title']}, URL: {img['url']}" for img in parsed_content.get('Brand Images', [])])

            user_prompt = f"""
            You must include at least 3 embedded images, although 10 is preferred. Do not invent links. Do not invent information. Generate a detailed 20 titles and sub and 2 paragraph per title {content_type} using the selected pages, products, blogs, and brand images, output in Markdown, with a lot of interesting formatting such as lists, tables, internal links and embedded images. This helps wtih ranking on Google. The end result should be a journalistic style piece of content on the topic.:
            Pages:
            {formatted_pages}

            Products:
            {formatted_products}

            Blogs:
            {formatted_blogs}

            Brand Images:
            {formatted_images}

            Please ensure the content is relevant and engaging, utilizing the provided information effectively.
            The content should be written in a {article_tone} tone and framed as {article_framing}.
            Incorporate the brand guidelines:
            {brand_guidelines}

            If applicable, mention the business type: {business_type}
            If applicable, mention or quote the famous person: {famous_person}
            """

            content = generate_content("System Prompt Here", user_prompt, anthropic_api_key)

            if content:
                if isinstance(content, list):
                    content = "\n".join([block.text for block in content])  # Extract text from ContentBlock objects and join them
                filename = f"generated_{content_type}_{keyword.replace(' ', '_')}.txt"
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(content)
                print(f"Content generated for keyword: {keyword}, and saved.")
            else:
                print("Failed to generate content for keyword:", keyword)
        else:
            print(f"Failed to retrieve or parse content for keyword: {keyword}")
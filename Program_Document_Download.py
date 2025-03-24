import requests
from bs4 import BeautifulSoup
import pdfkit
import os

# ヘッダーの強化
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Referer': 'https://armstradelitigationmonitor.org/',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Connection': 'keep-alive'
}

def scrape_page(url):
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve {url}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    link_elements = soup.select('a.real-link')
    urls = [link.get('href') for link in link_elements]
    
    return urls

def crawl_pages(base_url):
    all_urls = []
    page_number = 1
    
    while True:
        url = base_url if page_number == 1 else f"{base_url}page/{page_number}/"
        print(f"Scraping {url}")
        urls = scrape_page(url)
        
        if not urls:
            print(f"No more pages to scrape. Stopping at page {page_number}.")
            break
        
        all_urls.extend(urls)
        page_number += 1
    
    return all_urls

def scrape_document_data(url):
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve {url}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    documents_container = soup.find('div', id='documents', class_='documents margins-container')
    if not documents_container:
        print(f"No documents container found on {url}")
        return []
    
    data = []
    docs_elements = documents_container.find_all('div', class_='accordion-el docs')
    
    for docs in docs_elements:
        document_items = docs.find_all('div', class_='document')
        
        for item in document_items:
            date_tag = item.find('p', class_='date')
            title_tag = item.find('h4')
            if date_tag and title_tag:
                date = date_tag.text.strip()
                title = title_tag.text.strip().replace("/", "-").replace("\\", "-")
                
                link_tag = item.find('a', class_='blue-link')
                doc_url = link_tag.get('href')
                
                sub_response = requests.get(doc_url, headers=headers)
                if sub_response.status_code == 200:
                    sub_soup = BeautifulSoup(sub_response.text, 'html.parser')
                    document_section = sub_soup.find('div', class_='documents')
                    found_links = []
                    
                    if document_section:
                        download_links = document_section.find_all('a', target="_blank", download=True)
                        for dl_link in download_links:
                            href = dl_link.get('href')
                            if href and href not in found_links:
                                found_links.append(href)
                        
                        target_blank_links = document_section.find_all('a', target='_blank')
                        for tb_link in target_blank_links:
                            href = tb_link.get('href')
                            if href and href.endswith('.pdf') and href not in found_links:
                                found_links.append(href)
                
                data.append({
                    'Date': date,
                    'Title': title,
                    'Document URLs': found_links if found_links else [doc_url]
                })
    
    return data

def download_file(url, save_path):
    try:
        response = requests.get(url, headers=headers, stream=True)
        
        if url.endswith('.pdf') and response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Downloaded: {save_path}")
        elif response.status_code == 200:
            print(f"{url} is not a PDF, saving page as PDF.")
            save_page_as_pdf(url, save_path)
        else:
            print(f"Failed to download file from {url}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error downloading file from {url}: {e}")

def save_page_as_pdf(url, save_path):
    try:
        pdfkit.from_url(url, save_path)
        print(f"Saved page as PDF: {save_path}")
    except Exception as e:
        print(f"Failed to save page as PDF: {e}")

def process_document_urls(data, save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    for doc in data:
        doc_urls = doc['Document URLs']
        title = doc['Title']
        date = doc['Date'].replace("/", "-")
        
        for idx, doc_url in enumerate(doc_urls, start=1):
            file_name = f"{title}_{date}_{idx}.pdf"
            save_path = os.path.join(save_dir, file_name)
            
            if doc_url:
                download_file(doc_url, save_path)
            else:
                print(f"No valid URL found for {title}. Skipping.")

if __name__ == "__main__":
    base_url = "https://armstradelitigationmonitor.org/cases-index/"
    urls = crawl_pages(base_url)
    
    for target_url in urls:
        print(f"Scraping documents from {target_url}")
        document_data = scrape_document_data(target_url)
        save_directory = "downloaded_documents"
        process_document_urls(document_data, save_directory)

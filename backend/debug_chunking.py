"""Debug script to test chunking."""
from app.services.pdf_processor import PDFProcessor

proc = PDFProcessor(chunk_size=500, overlap=50, min_chunk_size=100)
pdf_path = '/app/example-file-upload/O992-ILF-OD-0012_Water Resources_RevFinal.pdf'

print("Extracting text...")
data = proc.extract_text_from_pdf(file_path=pdf_path)
print(f"Total words: {data['total_words']}")
print(f"Total pages: {data['total_pages']}")

# Test with first 1000 words
text_sample = ' '.join(data['full_text'].split()[:1000])
print(f"\nTesting with {len(text_sample.split())} words...")

sentences = proc._split_into_sentences(text_sample)
print(f"Sentences found: {len(sentences)}")

if sentences:
    print(f"\nFirst sentence: {sentences[0][:150]}")

    # Try creating chunks from sample
    sample_data = {
        'full_text': text_sample,
        'pages': data['pages'][:10],
        'total_pages': 10
    }

    chunks = proc.create_semantic_chunks(sample_data)
    print(f"\nChunks created from sample: {len(chunks)}")

    if chunks:
        print(f"First chunk word count: {chunks[0].word_count}")
        print(f"First chunk text (first 200 chars): {chunks[0].text[:200]}")
    else:
        print("No chunks created - debugging needed")
else:
    print("No sentences found - sentence splitting issue")

# chatbot
 
## Development

1. Clone the repo or download the ZIP

```
git clone [github https url]
```

2. Install packages

```
pip install -r requirements.txt
```


After installation, you should now see a `node_modules` folder.

3. Set up your `.env` file

- Copy `.env.example` into `.env`
  Your `.env` file should look like this:

```
OPENAI_API_KEY=
PINECONE_API_KEY=
PINECONE_ENVIRONMENT=
PINECONE_INDEX_NAME=
```
## Features

1. **File Upload Capability**
   - Upload documents in various formats: .pdf, .docx, .html, .csv, etc., for a versatile chatbot experience.

2. **Document Text Segmentation**
   - Access text segments from documents used by the Language Model (LLM) to answer questions, ensuring transparency and source insight.

3. **User Independence**
   - Create and manage unlimited users independently, allowing personalized usage of the chatbot service.

4. **Library Creation Freedom**
   - Users can create any number of libraries, fostering organization and personalization.

5. **Chat Export in TXT Format**
   - Export chat interactions in a text (.txt) format for easy archiving, sharing, or analysis.

6. **Vector Database Exploration**
   - Explore vector database data effortlessly and export it in CSV format, promoting transparency and data-driven insights.

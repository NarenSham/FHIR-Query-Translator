# FHIR Database Query Translator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A powerful Python tool that translates natural language questions into optimized SQL queries for FHIR (Fast Healthcare Interoperability Resources) databases. Leveraging Google's Gemini AI, this tool enables healthcare professionals and developers to query complex FHIR data structures using simple English questions.

## 🚀 Features

- **Natural Language Processing**: Convert plain English questions into precise SQL queries
- **FHIR-Optimized**: Built specifically for FHIR database schemas
- **Smart JSONB Handling**: Intelligent parsing and querying of JSONB fields in PostgreSQL
- **Context-Aware**: Maintains context across multiple queries
- **Type Safety**: Validates and sanitizes all inputs for secure database operations
- **Performance Optimized**: Generates efficient SQL queries with proper indexing considerations

## 📋 Prerequisites

- Python 3.8 or higher
- PostgreSQL database with FHIR data structure
- Google AI API key
- Basic understanding of FHIR data models

## 🔧 Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/fhir-query-translator.git
cd fhir-query-translator
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

3. Install required packages:

```bash
pip install -r requirements.txt
```

4. Set up environment variables:

```bash
cp .env.example .env
```
Edit .env with your configuration

## ⚙️ Configuration

Create a `.env` file in the root directory with the following variables:

```env
DB_HOST=your_database_host
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
GOOGLE_AI_API_KEY=your_google_ai_api_key
```

## 📖 Usage

### Basic Usage

```python
from query_translator import QueryTranslator
```
Initialize the translator
translator = QueryTranslator()
Simple query
result = translator.process_question("Show me all patients with diabetes")
print(result["results"])
Complex query with conditions
result = translator.process_question(
"Find female patients over 65 with hypertension diagnosed in the last 5 years"
)
print(result["sql"]) # View the generated SQL
print(result["results"]) # View the query results

### Advanced Features

```python

Custom database configuration
config = {
"host": "localhost",
"port": 5432,
"database": "fhir_db",
"user": "admin",
"password": "secure_password"
}
translator = QueryTranslator(
db_config=config,
ai_key="your_api_key",
context_window=5 # Remember context from last 5 queries
)
```
### Query with context
translator.process_question("Show me their medication history") # Uses context from previous query


## 📚 Example Queries

Here are some example questions you can ask:

- "Show all patients diagnosed with COVID-19 in 2023"
- "List the most common medications prescribed last month"
- "Find patients who had surgery in the past 6 months"
- "Show me vaccination records for pediatric patients"
- "What is the average length of hospital stays for cardiac patients?"

## 🔍 Query Structure

The translator handles various query components:
- Patient demographics
- Conditions and diagnoses
- Medications and prescriptions
- Procedures and surgeries
- Lab results and observations
- Appointments and encounters

## 🛠️ Development

### Running Tests

```bash
pytest tests/
```


### Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

For support, please:
- Open an issue in the GitHub repository
- Check existing documentation
- Review closed issues for similar problems

## 🙏 Acknowledgments

- FHIR® is the registered trademark of HL7
- Built with Google's Gemini AI technology
- Inspired by the healthcare interoperability community

## 📝 Citation

If you use this tool in your research, please cite:

```bibtex
@software{fhir_query_translator,
author = @narensham,
title = {FHIR Database Query Translator},
year = {2025},
publisher = {GitHub},
url = {https://github.com/narensham/fhir-query-translator}
}
```

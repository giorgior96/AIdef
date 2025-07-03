# 🚤 Boat Filter AI

A powerful AI-powered boat search application that uses natural language queries to filter through boat datasets. Built with Streamlit, Polars, and Google Gemini AI.

## ✨ Features

- **Natural Language Queries**: Ask for boats in plain English
- **Consistent Output**: Always displays name, price, and year
- **Beautiful UI**: Modern, responsive web interface
- **Fast Performance**: Uses Polars for efficient data processing
- **AI-Powered**: Leverages Google Gemini for intelligent query understanding

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key (free at [Google AI Studio](https://makersuite.google.com/app/apikey))

### Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key**:
   - Create a `.env` file in the project directory
   - Add your Gemini API key using the variable `GEMINI_API_KEYS`:
     ```
     GEMINI_API_KEYS=your_api_key_here
     ```
   - The application reads this variable via `os.getenv`, so you can also set it
     in your shell environment.

4. **Prepare your dataset**:
   - Place your boat data JSON file as `output_with_contact.json` in the project directory
   - The file should contain boat information with columns like name, price, year, etc.

### Running the Application

#### Option 1: Streamlit Web App (Recommended)
```bash
streamlit run app.py
```
This will open a beautiful web interface at `http://localhost:8501`

#### Option 2: Command Line Interface
```bash
python filters3.py
```

## 📊 Dataset Format

Your JSON dataset should contain boat information. Example structure:
```json
[
  {
    "boat_name": "Ocean Explorer 45",
    "price": 850000,
    "year": 2022,
    "length": 13.7,
    "max_speed": 25,
    "engine_type": "Diesel"
  }
]
```

## 🔍 Example Queries

Try these natural language queries:

- "Show me boats under €500,000"
- "Find boats built after 2020"
- "Show me boats with max speed over 30 knots"
- "Find boats between 10 and 15 meters long"
- "Show me the most expensive boats"
- "Find boats with diesel engines"

## 🎨 UI Features

- **Responsive Design**: Works on desktop and mobile
- **Real-time Search**: Instant results as you type
- **Example Queries**: Click-to-use sample queries
- **Data Preview**: See available columns and sample data
- **Beautiful Cards**: Each boat displayed in an attractive card format
- **Price Formatting**: Automatic formatting (€1.2M, €500K)
- **Year Highlighting**: Clear year display

## 🚀 Deployment Options

### 1. Streamlit Cloud (Easiest)
1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Set environment variables for your API key
5. Deploy!

### 2. Heroku
1. Create a `Procfile`:
   ```
   web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
   ```
2. Deploy using Heroku CLI or GitHub integration

### 3. Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 4. Local Network
```bash
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

## 🔧 Configuration

### Environment Variables
The application looks for a Gemini API key in the environment.
- `GEMINI_API_KEYS`: Your Google Gemini API key. It can be set in a `.env`
  file or directly in your shell environment.

### Customization
- Modify column mappings in `app.py` to match your dataset
- Adjust styling in the CSS section
- Change the default model in the sidebar

## 📁 Project Structure

```
├── app.py              # Streamlit web application
├── filters3.py         # Command-line version
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── .env               # Environment variables (create this)
└── output_with_contact.json  # Your boat dataset
```

## 🛠️ Development

### Adding New Features
1. The core logic is in the utility functions
2. UI components are in the display functions
3. Main app logic is in the `main()` function

### Testing
- Test with different query types
- Verify column mapping works with your dataset
- Check error handling with invalid queries

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is open source and available under the MIT License.

## 🆘 Support

If you encounter issues:
1. Check that your API key is valid
2. Verify your dataset format
3. Ensure all dependencies are installed
4. Check the console for error messages

## 🎯 Roadmap

- [ ] Add filters for boat type (sailboat, motorboat, etc.)
- [ ] Implement sorting options
- [ ] Add image support for boats
- [ ] Export results to CSV/PDF
- [ ] Multi-language support
- [ ] Advanced analytics dashboard

---

**Made with ❤️ using Streamlit, Polars, and Google Gemini AI** 
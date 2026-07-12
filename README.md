OptiCrop - Smart Agricultural Production Optimization Engine using Machine Learning

Project Overview

This project recommends the most suitable crop using Machine Learning techniques. The application analyzes important soil and environmental indicators such as Nitrogen (N), Phosphorous (P), Potassium (K) levels, temperature, humidity, soil pH, and rainfall to estimate the best-fit crop. A Flask-based web application provides a simple user interface where users can enter these indicators and obtain a predicted crop recommendation instantly.

Objectives:
Recommend the most suitable crop based on soil and environmental parameters.
Perform data preprocessing and visualization.
Train and compare multiple Machine Learning models.
Evaluate model performance.
Deploy the trained model using Flask.
Provide a simple web interface for predictions.

Features:
Dataset preprocessing
Missing value handling
Data visualization
K-Nearest Neighbors, Logistic Regression, Decision Tree, Random Forest and K-Means Clustering
Model evaluation using accuracy and classification metrics
Model serialization using Pickle
Flask web application
User-friendly prediction interface
Export prediction results (input values, predicted crop, and ID) as a CSV file

Technology Stack:
Python
Pandas
NumPy
Matplotlib
Seaborn
Scikit-learn
Flask
HTML
CSS
Bootstrap
Pickle

Project Workflow:
Environment Setup
Import Libraries
Dataset Collection
Data Exploration
Data Visualization
Data Preprocessing
Feature Selection
Train-Test Split
Model Training (KNN, Logistic Regression, Decision Tree, Random Forest, K-Means)
Model Evaluation
Save Model
Flask Deployment

Dataset
The dataset contains crop recommendation indicators collected for agricultural analysis.

Main attributes include:
Nitrogen (N)
Phosphorous (P)
Potassium (K)
Temperature
Humidity
pH
Rainfall
Crop Label

Machine Learning Algorithm

Random Forest Classifier (best performing, compared against K-Nearest Neighbors, Logistic Regression, Decision Tree and K-Means Clustering)
The model learns the relationship between soil nutrients, environmental indicators and crop type to recommend the most suitable crop for new user inputs.

## Installation

1. Clone the repository:

```bash
git clone https://github.com/arshiyatanzeen/OPTICROP.git
```

2. Navigate to the project folder:

```bash
cd OPTICROP
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

4. Run the Flask application:

```bash
python app.py
```

5. Open your browser and visit:

```
http://127.0.0.1:5000/
```

Project Structure
database/
dataset/
model/
notebooks/
src/
static/
templates/
app.py
auth.py
database.py
model_training.py
README.md
requirements.txt
utils.py

Future Enhancements:
Live Weather API integration
Fertilizer recommendation system
Improve prediction accuracy with advanced models
Interactive dashboards
Cloud deployment
User authentication and prediction history

Team Members:
Pinjari Arshiya - Team Lead
Muthukuri Raghu - Team Member
Saisriram Tiruveedhi - Team Member
Shiva Shankar Vara Prasad Kuruva - Team Member
Uday Kiran - Team Member

Conclusion:
This project demonstrates the application of Machine Learning in agriculture to recommend the most suitable crop for a given set of soil and environmental conditions. By integrating data preprocessing, visualization, model development, and Flask deployment, it provides an end-to-end solution for crop recommendation. The system is scalable and can be extended with advanced machine learning algorithms and cloud deployment for real-world use.

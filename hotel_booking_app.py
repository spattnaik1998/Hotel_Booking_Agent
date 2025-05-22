# app.py - Main Flask Application
import os
import logging
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import warnings
from typing import Dict, Any

# Import CrewAI components
from crewai import Agent, Crew, Task, Process
from crewai_tools import ScrapeWebsiteTool, SerperDevTool
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# Warning control
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HotelBookingService:
    """Service class to handle hotel and restaurant research"""
    
    def __init__(self):
        self.search_tool = SerperDevTool()
        self.scrape_tool = ScrapeWebsiteTool()
        self.setup_agents()
        self.setup_tasks()
        self.setup_crew()
    
    def setup_agents(self):
        """Initialize the research agents"""
        self.hotel_researcher = Agent(
            role='Hotel Researcher',
            goal='Find the best hotels based on reviews, ratings, and price.',
            backstory="""You are a seasoned hotel researcher with extensive experience in finding 
            the best hotels for travelers. You have a keen eye for detail and a passion for 
            helping people find the perfect place to stay. You always provide accurate information 
            including hotel names, addresses, ratings, and price ranges.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.search_tool, self.scrape_tool]
        )
        
        self.restaurant_finder = Agent(
            role='Restaurant Researcher',
            goal='Find the best restaurants based on cuisine, reviews, and atmosphere.',
            backstory="""You are an experienced restaurant researcher with extensive experience 
            in finding the best restaurants for travelers. You have a keen eye for detail and 
            a passion for helping people find amazing dining experiences. You consider factors 
            like cuisine type, ambiance, location, and customer reviews.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.search_tool, self.scrape_tool]
        )
    
    def setup_tasks(self):
        """Initialize the research tasks"""
        self.research_hotel_task = Task(
            description="""Conduct thorough research to identify the top 5 hotels in {city}.
            Consider factors such as:
            - Customer reviews and ratings
            - Price range and value for money
            - Location and accessibility
            - Amenities and services
            
            For each hotel, provide:
            - Hotel name
            - Full address
            - Star rating
            - Average price per night
            - Key amenities
            - Brief description of what makes it special""",
            expected_output="""A comprehensive list of the top 5 hotels in {city} with detailed 
            information about each property including name, address, rating, price range, and 
            key features.""",
            agent=self.hotel_researcher
        )
        
        self.restaurant_search_task = Task(
            description="""Conduct thorough research to find the top 5 restaurants in {city}.
            Consider factors such as:
            - Customer reviews and ratings
            - Cuisine type and quality
            - Price range
            - Atmosphere and ambiance
            - Location
            
            For each restaurant, provide:
            - Restaurant name
            - Full address
            - Cuisine type
            - Price range
            - Rating
            - Signature dishes or specialties
            - Brief description""",
            expected_output="""A comprehensive list of 5 top-rated restaurants in {city} with 
            detailed information about cuisine, location, pricing, and specialties.""",
            agent=self.restaurant_finder
        )
    
    def setup_crew(self):
        """Initialize the CrewAI crew"""
        try:
            self.crew = Crew(
                agents=[self.hotel_researcher, self.restaurant_finder],
                tasks=[self.research_hotel_task, self.restaurant_search_task],
                manager_llm=ChatOpenAI(
                    model="gpt-4o-mini",  # Using more cost-effective model
                    temperature=0.3
                ),
                process=Process.hierarchical,
                verbose=True
            )
        except Exception as e:
            logger.error(f"Failed to setup crew: {str(e)}")
            raise
    
    def research_city(self, city: str) -> Dict[str, Any]:
        """
        Research hotels and restaurants for a given city
        
        Args:
            city (str): The city to research
            
        Returns:
            Dict[str, Any]: Research results
        """
        try:
            logger.info(f"Starting research for city: {city}")
            
            inputs = {'city': city}
            result = self.crew.kickoff(inputs=inputs)
            
            logger.info(f"Research completed for city: {city}")
            
            return {
                'status': 'success',
                'city': city,
                'results': str(result),
                'message': f'Successfully found recommendations for {city}'
            }
            
        except Exception as e:
            logger.error(f"Error during research: {str(e)}")
            return {
                'status': 'error',
                'city': city,
                'error': str(e),
                'message': 'Failed to complete research'
            }

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize the service
try:
    booking_service = HotelBookingService()
    logger.info("Hotel booking service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize service: {str(e)}")
    booking_service = None

@app.route('/')
def home():
    """Home page"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Hotel Booking Agent API',
        'version': '1.0.0'
    })

@app.route('/research', methods=['POST'])
def research_city():
    """
    Research endpoint for hotels and restaurants
    
    Expected JSON payload:
    {
        "city": "San Francisco"
    }
    """
    try:
        if not booking_service:
            return jsonify({
                'status': 'error',
                'message': 'Service not available'
            }), 503
        
        data = request.get_json()
        
        if not data or 'city' not in data:
            return jsonify({
                'status': 'error',
                'message': 'City parameter is required'
            }), 400
        
        city = data['city'].strip()
        
        if not city:
            return jsonify({
                'status': 'error',
                'message': 'City cannot be empty'
            }), 400
        
        # Perform research
        results = booking_service.research_city(city)
        
        if results['status'] == 'error':
            return jsonify(results), 500
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error in research endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Resource not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500

if __name__ == '__main__':
    # Check if required environment variables are set
    required_vars = ['OPENAI_API_KEY', 'SERPER_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        print(f"Please set the following environment variables: {missing_vars}")
        exit(1)
    
    # Run the application
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
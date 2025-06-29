"""
Python Web Backend Integration for Global Social Worker Chatbot
FIXED VERSION - Properly changes port and keeps all functionality working
"""

from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
import json
import datetime
import os
import logging
import webbrowser
import threading
from dataclasses import asdict

# Import your existing chatbot classes
try:
    from socialworkcountry import GlobalSocialWorkerChatbot, PatientProfile
    from input_validation import ValidatedInputCollector, GlobalInputValidator
except ImportError as e:
    print(f"Import Error: {e}")
    print("Make sure socialworkcountry.py and input_validation.py are in the same directory")

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom configuration - CHANGE THESE TO CUSTOMIZE
CUSTOM_PORT = 5000
CUSTOM_TITLE = "Professional Social Worker Assessment"
CUSTOM_BRAND = "SocialWorker Pro"

class WebSocialWorkerChatbot:
    """
    Web-enabled version of your Global Social Worker Chatbot
    Handles HTTP requests and returns JSON responses
    """

    def __init__(self):
        self.chatbot = GlobalSocialWorkerChatbot()
        self.validator = GlobalInputValidator()
        self.session_data = {}

    def validate_and_convert_patient_data(self, web_data):
        """Convert web form data to PatientProfile format with validation"""
        validation_errors = []

        field_mapping = {
            'name': 'name',
            'age': 'age',
            'country': 'country',
            'city': 'city',
            'gender': 'gender',
            'employment': 'employment_status',
            'financial': 'financial_status',
            'exercise': 'exercise_level',
            'mental': 'mental_state',
            'notes': 'additional_notes'
        }

        converted_data = {}

        for web_field, profile_field in field_mapping.items():
            value = web_data.get(web_field, '')

            if web_field == 'name':
                result = self.validator.validate_name(value)
            elif web_field == 'age':
                result = self.validator.validate_age(str(value))
                if result.is_valid:
                    value = result.value
            elif web_field == 'country':
                result = type('obj', (object,), {'is_valid': True, 'value': value})()
            elif web_field == 'city':
                country_code = web_data.get('country', '')
                result = self.validator.validate_city(value, country_code)
            elif web_field in ['gender', 'employment', 'financial', 'exercise']:
                value = self._convert_web_value_to_display(web_field, value)
                result = type('obj', (object,), {'is_valid': True, 'value': value})()
            elif web_field == 'mental':
                value = self._convert_web_value_to_display(web_field, value)
                result = self.validator.validate_mental_state(value)
            elif web_field == 'notes':
                result = self.validator.validate_additional_notes(value)
            else:
                result = type('obj', (object,), {'is_valid': True, 'value': value})()

            if not result.is_valid:
                validation_errors.append({
                    'field': web_field,
                    'message': result.error_message,
                    'suggestions': result.suggestions
                })
            else:
                converted_data[profile_field] = result.value if hasattr(result, 'value') else value

        if validation_errors:
            return None, validation_errors

        try:
            patient = PatientProfile(**converted_data)
            return patient, []
        except Exception as e:
            validation_errors.append({
                'field': 'general',
                'message': f"Failed to create patient profile: {str(e)}",
                'suggestions': ['Please check all fields are correctly filled']
            })
            return None, validation_errors

    def _convert_web_value_to_display(self, field, value):
        """Convert web form values to display format expected by chatbot"""
        conversions = {
            'gender': {
                'male': 'Male',
                'female': 'Female',
                'non_binary': 'Non-binary',
                'prefer_not_to_say': 'Prefer not to say'
            },
            'employment': {
                'full_time': 'Full-time employed',
                'part_time': 'Part-time employed',
                'unemployed_seeking': 'Unemployed - actively seeking',
                'unemployed_not_seeking': 'Unemployed - not seeking',
                'student': 'Student',
                'retired': 'Retired',
                'unable_to_work': 'Unable to work'
            },
            'financial': {
                'low_income': 'low_income',
                'moderate_income': 'moderate_income',
                'stable_income': 'stable_income'
            },
            'exercise': {
                'very_active': 'Very active',
                'moderately_active': 'Moderately active',
                'lightly_active': 'Lightly active',
                'sedentary': 'Sedentary'
            },
            'mental': {
                'excellent': 'Excellent',
                'good': 'Good',
                'fair': 'Fair',
                'poor': 'Poor',
                'critical': 'Critical'
            }
        }

        return conversions.get(field, {}).get(value, value)

    def generate_assessment(self, patient_data):
        """Generate complete assessment using your existing chatbot logic"""
        try:
            patient, validation_errors = self.validate_and_convert_patient_data(patient_data)

            if validation_errors:
                return {
                    'success': False,
                    'errors': validation_errors
                }

            country_health_needs = self.chatbot.assess_country_specific_health_needs(patient)
            country_safety_needs = self.chatbot.assess_country_specific_safety_needs(patient)
            country_evidence_recs = self.chatbot.generate_country_evidence_recommendations(patient)
            general_recommendations = self.chatbot.generate_comprehensive_recommendations(patient)

            country_data = self.chatbot.health_db.country_health_data.get(patient.country, {})

            assessment_result = {
                'success': True,
                'patient_profile': {
                    'name': patient.name,
                    'age': patient.age,
                    'country': patient.country.replace('_', ' ').title(),
                    'city': patient.city,
                    'gender': patient.gender,
                    'employment_status': patient.employment_status,
                    'financial_status': patient.financial_status.replace('_', ' ').title(),
                    'exercise_level': patient.exercise_level,
                    'mental_state': patient.mental_state,
                    'additional_notes': patient.additional_notes
                },
                'country_context': {
                    'name': patient.country.replace('_', ' ').title(),
                    'mental_health_prevalence': country_data.get('mental_health_prevalence', 0.20) * 100,
                    'healthcare_system': country_data.get('healthcare_system', 'Unknown').replace('_', ' ').title(),
                    'common_health_issues': country_data.get('common_health_issues', [])[:3],
                    'crisis_resources': country_data.get('crisis_resources', [])
                },
                'assessments': {
                    'country_health_needs': country_health_needs,
                    'country_safety_needs': country_safety_needs,
                    'country_evidence_recommendations': country_evidence_recs,
                    'general_recommendations': general_recommendations
                },
                'risk_indicators': self._assess_risk_level(patient),
                'timestamp': datetime.datetime.now().isoformat(),
                'age_category': self.chatbot.determine_age_category(patient.age),
                'city_category': self.chatbot.determine_city_category(patient.city, patient.country)
            }

            return assessment_result

        except Exception as e:
            logger.error(f"Assessment generation failed: {str(e)}")
            return {
                'success': False,
                'error': 'Assessment generation failed',
                'message': str(e)
            }

    def _assess_risk_level(self, patient):
        """Assess overall risk level for the patient"""
        risk_level = 'low'
        risk_factors = []

        if patient.mental_state == 'Critical':
            risk_level = 'critical'
            risk_factors.append('Critical mental health state')
        elif patient.mental_state == 'Poor':
            risk_level = 'high' if risk_level != 'critical' else risk_level
            risk_factors.append('Poor mental health state')

        if patient.additional_notes:
            crisis_keywords = ['suicide', 'kill myself', 'hurt myself', 'end it all', 'want to die']
            for keyword in crisis_keywords:
                if keyword in patient.additional_notes.lower():
                    risk_level = 'critical'
                    risk_factors.append('Crisis language detected in notes')
                    break

        if patient.age < 18:
            risk_factors.append('Minor patient - requires specialized care')
        elif patient.age > 75:
            risk_factors.append('Senior patient - increased health monitoring needed')

        if patient.mental_state in ['Poor', 'Critical'] and 'employed' in patient.employment_status.lower():
            risk_factors.append('Mental health concerns may impact work capacity')

        return {
            'level': risk_level,
            'factors': risk_factors,
            'requires_immediate_attention': risk_level in ['critical', 'high']
        }


# Initialize the web chatbot
web_chatbot = WebSocialWorkerChatbot()

# Main route - Serve the interactive website
@app.route('/')
def index():
    """Serve the main assessment page with proper port configuration"""
    try:
        # Read the original client.html
        with open('client.html', 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Update the title
        html_content = html_content.replace(
            '<title>Global Social Worker Assessment - Full Stack</title>',
            f'<title>{CUSTOM_TITLE}</title>'
        )

        # Update the header
        html_content = html_content.replace(
            '<h1>🌍 Global Social Worker Assessment</h1>',
            f'<h1>🏥 {CUSTOM_BRAND}</h1>'
        )

        # CRITICAL FIX: Update API URL to use the correct port
        html_content = html_content.replace(
            "API_BASE_URL = 'http://localhost:5000/api';",
            f"API_BASE_URL = 'http://localhost:{CUSTOM_PORT}/api';"
        )

        # Also fix any hardcoded references
        html_content = html_content.replace(
            'http://localhost:5000/api',
            f'http://localhost:{CUSTOM_PORT}/api'
        )

        logger.info(f"Successfully serving {CUSTOM_BRAND} from localhost:{CUSTOM_PORT}")
        return html_content

    except FileNotFoundError:
        logger.warning("client.html not found - serving fallback page")
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{CUSTOM_TITLE}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 40px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #4CAF50, #45a049);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .content {{
                    padding: 40px;
                }}
                .error {{
                    color: #d32f2f;
                    background: #ffebee;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border-left: 4px solid #f44336;
                }}
                .solution {{
                    color: #2e7d32;
                    background: #e8f5e8;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border-left: 4px solid #4caf50;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏥 {CUSTOM_BRAND}</h1>
                    <p>Running on Port {CUSTOM_PORT}</p>
                </div>

                <div class="content">
                    <div class="error">
                        <h2>❌ Interface File Missing</h2>
                        <p><strong>client.html is not found in the project directory</strong></p>
                    </div>

                    <div class="solution">
                        <h3>✅ To Fix:</h3>
                        <ol>
                            <li>Add client.html to your project folder</li>
                            <li>Restart the server</li>
                            <li>Refresh this page</li>
                        </ol>
                    </div>

                    <div style="text-align: center; margin-top: 30px;">
                        <h3>🔗 Backend Status: ✅ Running</h3>
                        <p>API endpoints are available on port {CUSTOM_PORT}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error serving index page: {str(e)}")
        return f"<h1>Server Error</h1><p>Error: {str(e)}</p>", 500

# API Routes
@app.route('/api/assess', methods=['POST'])
def assess_patient():
    """Main endpoint to assess a patient"""
    try:
        patient_data = request.get_json()

        if not patient_data:
            return jsonify({
                'success': False,
                'error': 'No data provided',
                'message': 'Please provide patient data in JSON format'
            }), 400

        logger.info(f"Assessment request for patient: {patient_data.get('name', 'Unknown')}")

        assessment_result = web_chatbot.generate_assessment(patient_data)

        if assessment_result.get('success'):
            logger.info(f"Assessment completed successfully for {patient_data.get('name', 'Unknown')}")
        else:
            logger.warning(f"Assessment failed: {assessment_result.get('error', 'Unknown error')}")

        return jsonify(assessment_result)

    except Exception as e:
        logger.error(f"Assessment endpoint error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Server error',
            'message': str(e)
        }), 500

@app.route('/api/validate', methods=['POST'])
def validate_field():
    """Validate individual fields (for real-time validation)"""
    try:
        data = request.get_json()
        field_name = data.get('field')
        field_value = data.get('value')
        context = data.get('context', {})

        if field_name == 'name':
            result = web_chatbot.validator.validate_name(field_value)
        elif field_name == 'age':
            result = web_chatbot.validator.validate_age(str(field_value))
        elif field_name == 'city':
            country = context.get('country', '')
            result = web_chatbot.validator.validate_city(field_value, country)
        else:
            return jsonify({
                'success': False,
                'message': f'Validation not implemented for field: {field_name}'
            })

        return jsonify({
            'success': True,
            'is_valid': result.is_valid,
            'message': result.error_message if not result.is_valid else 'Valid',
            'suggestions': result.suggestions
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/countries', methods=['GET'])
def get_countries():
    """Get list of available countries"""
    try:
        countries = []
        for country_code, country_data in web_chatbot.chatbot.health_db.country_health_data.items():
            countries.append({
                'code': country_code,
                'name': country_code.replace('_', ' ').title(),
                'crisis_resources': country_data.get('crisis_resources', []),
                'healthcare_system': country_data.get('healthcare_system', '').replace('_', ' ').title()
            })

        return jsonify({
            'success': True,
            'countries': countries
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/emergency-resources/<country_code>', methods=['GET'])
def get_emergency_resources(country_code):
    """Get emergency resources for a specific country"""
    try:
        country_data = web_chatbot.chatbot.health_db.country_health_data.get(country_code, {})

        if not country_data:
            return jsonify({
                'success': False,
                'error': 'Country not found'
            }), 404

        return jsonify({
            'success': True,
            'country': country_code.replace('_', ' ').title(),
            'crisis_resources': country_data.get('crisis_resources', []),
            'healthcare_system': country_data.get('healthcare_system', '').replace('_', ' ').title(),
            'mental_health_prevalence': country_data.get('mental_health_prevalence', 0.20) * 100
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/save-assessment', methods=['POST'])
def save_assessment():
    """Save assessment results to file"""
    try:
        data = request.get_json()
        patient_name = data.get('patient_name', 'Unknown')
        country = data.get('country', 'Unknown')
        assessment_data = data.get('assessment_data', {})

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"web_assessment_{patient_name.replace(' ', '_')}_{country}_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(assessment_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Assessment saved to file: {filename}")

        return jsonify({
            'success': True,
            'filename': filename,
            'message': 'Assessment saved successfully'
        })

    except Exception as e:
        logger.error(f"Error saving assessment: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'message': 'The requested resource was not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

if __name__ == '__main__':
    print("=" * 80)
    print(f"{CUSTOM_BRAND.upper()} - ASSESSMENT PLATFORM")
    print("=" * 80)
    print("🏥 Starting custom web server...")
    print(f"📍 Server will be available at: http://localhost:{CUSTOM_PORT}")
    print(f"📝 Interactive website: http://localhost:{CUSTOM_PORT}")
    print(f"🎯 Brand: {CUSTOM_BRAND}")
    print(f"🌟 Title: {CUSTOM_TITLE}")
    print("🔗 API endpoints:")
    print(f"   POST /api/assess - Submit patient assessment")
    print(f"   POST /api/validate - Validate individual fields")
    print(f"   GET /api/countries - Get available countries")
    print(f"   GET /api/emergency-resources/<country> - Get emergency contacts")
    print("=" * 80)
    print("💡 IMPORTANT: Make sure to stop any other servers running on port 5000!")
    print(f"🚀 Access your platform at: http://localhost:{CUSTOM_PORT}")
    print("=" * 80)

    # Automatically open browser after a short delay
    def open_browser():
        try:
            webbrowser.open(f'http://localhost:{CUSTOM_PORT}')
            print(f"🌐 Browser opened automatically to http://localhost:{CUSTOM_PORT}")
        except Exception as e:
            print(f"Could not open browser: {e}")

    # Start browser opener in separate thread
    threading.Timer(3.0, open_browser).start()

    # Run the Flask app on the custom port
    app.run(
        host='127.0.0.1',  # Localhost only
        port=CUSTOM_PORT,  # Use the custom port
        debug=True         # Enable debug mode
    )
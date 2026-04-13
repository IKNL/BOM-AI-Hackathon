from flask import Flask, request, jsonify, send_from_directory, make_response
from flask_cors import CORS
import json
import os
import mimetypes
from cancer_assistant import (
    load_cancer_mapping,
    load_markdown_content,
    chunk_markdown_by_sections,
    find_relevant_sections,
    query_with_context,
    find_best_match,
    onboarding_query
)

# Ensure proper MIME types
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('text/html', '.html')
mimetypes.add_type('image/png', '.png')
mimetypes.add_type('image/jpeg', '.jpg')

app = Flask(__name__, static_folder='.')
CORS(app)

# Load cancer mapping at startup
cancer_mapping = load_cancer_mapping()

# Store session data (in production, use proper session management)
sessions = {}

@app.route('/backend/onboard', methods=['POST'])
def onboard():
    """Handle onboarding conversation"""
    try:
        data = request.json
        message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Initialize session if needed
        if session_id not in sessions:
            sessions[session_id] = {
                'user_context': {},
                'conversation_history': [],
                'cancer_type': None,
                'sections': None,
                'onboarding_complete': False
            }
        
        session = sessions[session_id]
        
        # Check if user wants to skip
        if message.lower() == 'skip':
            session['onboarding_complete'] = True
            return jsonify({
                'response': 'Onboarding overgeslagen. U kunt nu direct vragen stellen.',
                'onboarding_complete': True
            })
        
        # Use onboarding_query to process the message
        result = onboarding_query(message, session['user_context'])
        
        # Update context
        if result.get('context_update'):
            session['user_context'].update(result['context_update'])
        
        # Check if cancer type identified
        cancer_type = session['user_context'].get('cancer_type')
        if cancer_type and result.get('onboarding_complete'):
            matched_type = find_best_match(cancer_type, cancer_mapping)
            if matched_type:
                md_file = cancer_mapping[matched_type]
                content = load_markdown_content(md_file)
                if content:
                    session['cancer_type'] = matched_type
                    session['sections'] = chunk_markdown_by_sections(content)
                    session['onboarding_complete'] = True
                    
                    # Fill in missing context with defaults
                    if 'wellbeing' not in session['user_context']:
                        session['user_context']['wellbeing'] = 'niet gespecificeerd'
                    if 'age' not in session['user_context']:
                        session['user_context']['age'] = 'niet gespecificeerd'
                    if 'gender' not in session['user_context']:
                        session['user_context']['gender'] = 'niet gespecificeerd'
                    if 'answer_style' not in session['user_context']:
                        session['user_context']['answer_style'] = 'eenvoudig en begrijpelijk'
                    
                    return jsonify({
                        'response': f'Bedankt! Ik heb informatie over {matched_type} geladen. Stel gerust uw vragen.',
                        'onboarding_complete': True,
                        'cancer_type': matched_type
                    })
        
        return jsonify({
            'response': result.get('response', ''),
            'onboarding_complete': False
        })
        
    except Exception as e:
        print(f"Error in onboarding: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """Serve homepage"""
    return send_from_directory('.', 'homePage.html')

@app.route('/homePage.html')
def home():
    """Serve homepage"""
    return send_from_directory('.', 'homePage.html')

@app.route('/chatBotPage.html')
def chatbot():
    """Serve chatbot page"""
    return send_from_directory('.', 'chatBotPage.html')

@app.route('/css/<path:filename>')
def serve_css(filename):
    """Serve CSS files with explicit MIME type"""
    try:
        response = make_response(send_from_directory('css', filename))
        response.headers['Content-Type'] = 'text/css; charset=utf-8'
        response.headers['Cache-Control'] = 'no-cache'
        return response
    except Exception as e:
        print(f"Error serving CSS {filename}: {e}")
        return str(e), 404

@app.route('/images/<path:filename>')
def serve_images(filename):
    """Serve image files"""
    return send_from_directory('images', filename)

@app.route('/backend/ask', methods=['POST'])
def ask():
    """Handle user questions"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        session_id = data.get('session_id', 'default')
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        # Initialize session if needed
        if session_id not in sessions:
            sessions[session_id] = {
                'user_context': {'answer_style': 'eenvoudig en begrijpelijk'},
                'conversation_history': [],
                'cancer_type': None,
                'sections': None,
                'onboarding_complete': False
            }
        
        session = sessions[session_id]
        
        # Check if onboarding is complete
        if not session.get('onboarding_complete'):
            return jsonify({
                'error': 'Onboarding not complete',
                'needs_onboarding': True
            }), 400
        
        # Check if cancer type is mentioned in question
        if not session['cancer_type']:
            matched_type = find_best_match(question, cancer_mapping)
            if matched_type:
                # Load markdown for this cancer type
                md_file = cancer_mapping[matched_type]
                content = load_markdown_content(md_file)
                if content:
                    session['cancer_type'] = matched_type
                    session['sections'] = chunk_markdown_by_sections(content)
                    session['user_context']['cancer_type'] = matched_type
        
        # If still no cancer type, try to extract it via onboarding
        if not session['cancer_type']:
            try:
                result = onboarding_query(question, session['user_context'])
                if result.get('context_update'):
                    session['user_context'].update(result['context_update'])
                    cancer_type = session['user_context'].get('cancer_type')
                    if cancer_type:
                        matched_type = find_best_match(cancer_type, cancer_mapping)
                        if matched_type:
                            md_file = cancer_mapping[matched_type]
                            content = load_markdown_content(md_file)
                            if content:
                                session['cancer_type'] = matched_type
                                session['sections'] = chunk_markdown_by_sections(content)
            except:
                pass
        
        # If we have cancer type and sections, query with context
        if session['cancer_type'] and session['sections']:
            result = query_with_context(
                question,
                session['sections'],
                session['cancer_type'].title(),
                session['user_context'],
                session['conversation_history']
            )
            
            # Store in conversation history
            session['conversation_history'].append((question, result['response']))
            
            return jsonify({
                'answer': result['response'],
                'next_topics': result.get('next_topics', []),
                'sources': result.get('references', []),
                'cancer_type': session['cancer_type']
            })
        else:
            # No cancer type identified yet
            return jsonify({
                'answer': 'Over welk type kanker wilt u informatie? (Bijvoorbeeld: blaaskanker, borstkanker, longkanker)',
                'next_topics': [],
                'sources': []
            })
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/backend/reset', methods=['POST'])
def reset():
    """Reset session"""
    data = request.json
    session_id = data.get('session_id', 'default')
    if session_id in sessions:
        del sessions[session_id]
    return jsonify({'status': 'reset'})

@app.route('/backend/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'cancer_types_loaded': len(cancer_mapping)
    })

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Backend API starting on port {port}...")
    print(f"Loaded {len(cancer_mapping)} cancer types")
    print(f"\nAccess the application at: http://localhost:{port}/")
    app.run(host='0.0.0.0', port=port, debug=True)
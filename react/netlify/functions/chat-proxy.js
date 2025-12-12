// Function: chat-proxy.js
// Purpose: Acts as a secure intermediary (proxy) between the React frontend 
//          (running on Netlify) and the external FastAPI backend.
//          This prevents CORS issues and hides the backend URL.
// We retrieve the external backend URL from Netlify's environment variables.

const BACKEND_URL = process.env.VITE_BASE_API_URL; 

exports.handler = async (event, context) => {
    
    // Input Validation: Ensure it's a POST request (standard for chat)
    if (event.httpMethod !== 'POST') {
        return {
            statusCode: 405,
            body: JSON.stringify({ error: 'Method Not Allowed. Only POST requests are supported.' }),
        };
    }
    
    // Security Check: Ensure the backend URL is actually configured
    if (!BACKEND_URL) {
        console.error("VITE_BASE_API_URL environment variable is missing!");
        return {
            statusCode: 500,
            body: JSON.stringify({ error: 'Server misconfiguration: Backend URL is not defined.' }),
        };
    }

    try {
        // Make the Request to the External Backend
        const response = await fetch(`${BACKEND_URL}/chat`, {
            method: 'POST',
            // Forward the original request headers for content type
            headers: {
                'Content-Type': 'application/json',
            },
            body: event.body, // The JSON payload (user message) from the React app
        });

        // Handle HTTP errors from the external backend
        if (!response.ok) {
            const errorBody = await response.text();
            console.error(`Backend returned status ${response.status}: ${errorBody}`);
            return {
                statusCode: response.status,
                body: JSON.stringify({ error: `Backend API failed: ${response.statusText}` }),
            };
        }

        // Success: Get the JSON response from the backend
        const data = await response.json();
        
        // Return the final response to the React client
        return {
            statusCode: 200,
            // Ensure the content type is correct for the React app
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        };

    } catch (error) {
        // Handle network/fetch errors (e.g., DNS failure, timeout)
        console.error('Netlify Proxy Error during fetch:', error);
        return {
            statusCode: 502, // Bad Gateway status code for upstream server error
            body: JSON.stringify({ error: 'Failed to connect to the external API server.' }),
        };
    }
};
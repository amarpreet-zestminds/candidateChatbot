import os
import json
import boto3
from botocore.exceptions import ClientError
from openai import OpenAI
from simple_salesforce import Salesforce
import time
import uuid
import traceback
from datetime import datetime
import pytz
import re

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',  # Replace '*' with your domain for security
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

# DynamoDB Configuration
dynamodb = boto3.resource('dynamodb')
table_name = "users_info"
error_table_name = "chatbot_errors"

# Initialize OpenAI Configuration
OPENAI_API_KEY = os.getenv('OpenAI_API')
ASSISTANT_ID = os.getenv('ASSISTANT_ID')

client = OpenAI(api_key=OPENAI_API_KEY)

pst = pytz.timezone("US/Pacific")
current_time_pst = datetime.now(pst)
formatted_time = current_time_pst.strftime("%m/%d/%Y %I:%M:%S %p")

# Salesforce Configuration
SF_USERNAME = os.getenv('SF_USERNAME')
SF_PASSWORD = os.getenv('SF_PASSWORD')
SF_TOKEN = os.getenv('SF_TOKEN')
SF_DOMAIN = "login"  # Set domain to "login" for production

# Validate environment variables
if not OPENAI_API_KEY:
    raise ValueError("Environment variable OPENAI_API_KEY is not set.")
if not ASSISTANT_ID:
    raise ValueError("Environment variable ASSISTANT_ID is not set.")


def get_openai_summary(messages, candidateInfoErrorCase):
        try:
            # Construct the messages payload
            message_payload = [
                {"role": "system", "content": "Summarize the support chat conversation below. Comment on multiple aspects of the ticket, resolution steps attempted, questions asked, and reason for escalation. Also note whether the user seems content or unhappy."},
                {"role": "user", "content": json.dumps(messages)}
            ]
            
            print("start of openAI")
            # Call the OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=message_payload,
                temperature=0.7,
                max_tokens=5000  # Adjust max tokens
            )
            
            # Extract the response content
            reply = response.choices[0].message.content
            return reply
        
        except Exception as e:
            # Handle any exceptions that may occur
            error_table = dynamodb.Table(error_table_name)
            error_table.put_item(Item={
                        "createdAtPST":formatted_time, "conversationId":candidateInfoErrorCase['conversationId'], "Email":candidateInfoErrorCase['email'], "Name":candidateInfoErrorCase['name'], "Error":f"Openai summary error - {str(e)}"
                        })
            return f"Error: {str(e)}"


def get_openai_chats_formatted(messages, candidateInfoErrorCase):
        try:
            # Construct the messages payload
            message_payload = [
                {"role": "system", "content": "Make a chat history that is human readable from the details below. Put Candidate next to each candidate (user) message and Criteria next to any Assistant message. Add new lines \ n where appropriate. Remove any html tags. Don't skip any, even if they are duplicates."},
                {"role": "user", "content": json.dumps(messages)}
            ]
            
            print("start of openAI")
            # Call the OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=message_payload,
                temperature=0.7,
                max_tokens=1000  # Adjust max tokens
            )
            
            # Extract the response content
            reply = response.choices[0].message.content
            return reply
        
        except Exception as e:
            # Handle any exceptions that may occur
            error_table = dynamodb.Table(error_table_name)
            error_table.put_item(Item={
                        "createdAtPST":formatted_time, "conversationId":candidateInfoErrorCase['conversationId'], "Email":candidateInfoErrorCase['email'], "Name":candidateInfoErrorCase['name'], "Error":f"Openai chats error - {str(e)}"
                        })
            return f"Error: {str(e)}"

def def_openai_chats_subject(messages, candidateInfoErrorCase):
        try:
            # Construct the messages payload
            message_payload = [
                {"role": "system", "content": "Make a concise 5 word summary that will become the Subject line of a support case ticket representing this chat."},
                {"role": "user", "content": json.dumps(messages)}
            ]
            
            print("start of openAI")
            # Call the OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=message_payload,
                temperature=0.7,
                max_tokens=1000  # Adjust max tokens
            )
            
            # Extract the response content
            reply = response.choices[0].message.content
            return reply
        
        except Exception as e:
            # Handle any exceptions that may occur
            error_table = dynamodb.Table(error_table_name)
            error_table.put_item(Item={
                        "createdAtPST":formatted_time, "conversationId":candidateInfoErrorCase['conversationId'], "Email":candidateInfoErrorCase['email'], "Name":candidateInfoErrorCase['name'], "Error":f"Openai subject error - {str(e)}"
                        })
            return f"Error: {str(e)}"



#Create SalesForce Ticket
def create_salesforce_case(subject: str, description: str, candidateInfoErrorCase: dict):
    try:
        # Authenticate with Salesforce
        sf = Salesforce(
            username=SF_USERNAME,
            password=SF_PASSWORD,
            security_token=SF_TOKEN,
            domain=SF_DOMAIN
        )
    except Exception as e:
        error_table = dynamodb.Table(error_table_name)
        error_table.put_item(Item={
                        "createdAtPST":formatted_time, "conversationId":candidateInfoErrorCase['conversationId'], "Email":candidateInfoErrorCase['email'], "Name":candidateInfoErrorCase['name'], "Error":f"Salesforce authentication failed - {str(e)}"
                        })
        
        print(f"Salesforce authentication failed: {str(e)}")
        return {'success': False, 'case_id': None, 'error': f"Authentication failed: {str(e)}"}

    # Define Case fields
    case_data = {
        'Subject': subject,
        'Description': description,
        'Origin': 'Web',
        'Status': 'New',
        #'Type': 'Candidate_Support_Queue',
        'OwnerId': '00GUT000001nw3t2AA',
        'RecordTypeId': '012UT000000gp9NYAQ'
    }
    try:
        # Create a case
        result = sf.Case.create(case_data)
        case_id = result.get('id')
        print(f"Salesforce Case Created: {case_id}")
        return {'success': True, 'case_id': case_id, 'error': None}
    except Exception as e:
        error_table = dynamodb.Table(error_table_name)
        error_table.put_item(Item={
                        "createdAtPST":formatted_time, "conversationId":candidateInfoErrorCase['conversationId'], "Email":candidateInfoErrorCase['email'], "Name":candidateInfoErrorCase['name'], "Error":f"Failed to create Salesforce case - {str(e)}"
                        })
        
        print(f"Failed to create Salesforce case: {str(e)}")
        return {'success': False, 'case_id': None, 'error': str(e)}


# Function to save user data to DynamoDB
def save_user_data(time, name, email, emp_name, event_id, conversationId, thread_id):
    try:
        user_data = {
            'email': email,
            'name': name,
            'employer_name': emp_name,
            'event_id': event_id,
            'conversationId': conversationId,
            'thread_id': thread_id,
            'messages': [{"content":"Hi there! I'm Criteria's Candidate Support Bot. How can I help you today?","role":"assistant","message_time":time}],  # Initialize empty message history
            'createdAt': time
        }
        table = dynamodb.Table(table_name)
        table.put_item(Item=user_data)
        print(f"Data saved to DynamoDB: {user_data}")
        return user_data
    except ClientError as e:
        error_table = dynamodb.Table(error_table_name)
        error_table.put_item(Item={
                        "createdAtPST":formatted_time, "conversationId":conversationId, "Email":email, "Name":name, "Error":f"Error saving candidate data to DynamoDB - {str(e)}"
                        })
        
        print(f"Error saving to DynamoDB: {e}")
        raise

def handle_user_message(conversationId, user_message, localTime):
    try:
        table = dynamodb.Table(table_name)

        # Fetch existing conversation
        response = table.get_item(Key={'conversationId': conversationId})
        if 'Item' not in response:
            # return {'error': 'Conversation not found.'}
            return {'error': 'Session Expired. Restart the Chat!'}

        conversation = response['Item']
        thread_id = conversation.get('thread_id')
        email_address = conversation.get('email')
        employer_name = conversation.get('employer_name')
        candidate_name = conversation.get('name')
        event_id = conversation.get('eventid')
        salesid = conversation.get('eventid')
        print(salesid)
        
        if not thread_id:
            return {'error': 'Thread ID not found for this conversation.'}

        if not user_message or user_message == '':
            messages = conversation.get('messages', [])
            return {'response': messages}

        messages = conversation.get('messages', [])

        # Append the user's message to the history
        messages.append({"role": "user", "content": user_message, "message_time": localTime})

        # Initialize OpenAI client

        # Send the user's message
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )
        print("User message sent to OpenAI.")

        # Stream assistant's response
        assistant_response = ""


        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )


        openai_msgs = client.beta.threads.messages.list(thread_id=thread_id)

        #Implemented Polling method
        while True:
            run_details = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            # Check if run_details.completed_at is set (no longer None)
            if run_details.completed_at is not None:
                openai_msgs = client.beta.threads.messages.list(thread_id=thread_id)
                assistant_response = openai_msgs.data[0].content[0].text.value
                print("Run is completed.")
                break
            else:
                print("Run not completed yet. Waiting a bit...")
                # Sleep to avoid spamming the API too frequently
                time.sleep(3)
                #test


        #Salesforce Logic

        # Check if assistant_response contains the trigger text
        if "{{CREATE_SUPPORT_TICKET}}" in assistant_response:
            # Escalation flow: create a Salesforce case
            candidateInfoErrorCase = {"conversationId":conversationId, "name":candidate_name, "email":email_address}

            candidate_info = f"Name: {candidate_name} / Email: {email_address} / Prosp Employer: {employer_name} / EventID: {event_id}"
            chat_transcript =  get_openai_chats_formatted(messages, candidateInfoErrorCase)

            subject = "AI ChatBot: " + def_openai_chats_subject(messages, candidateInfoErrorCase)
            description = f"\n\nCASE AI SUMMARY: {get_openai_summary(messages, candidateInfoErrorCase)}\n\n\n Candidate Info: \n{candidate_info}\n\n\n\nTranscript: \n{chat_transcript}"

            sf_response = create_salesforce_case(subject, description, candidateInfoErrorCase)
            if sf_response['success']:
                table.update_item(
                    Key={'conversationId': conversationId},
                    UpdateExpression="SET salesforce_id = :sf_id",
                    ExpressionAttributeValues={':sf_id': json.dumps(sf_response['case_id'])}
                )
            else:
                return {
                    'statusCode': 500,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({'error': sf_response['error']})
                }

        # Update DynamoDB
        # Append assistant's response
        assistant_response = re.sub(r'【.*?】', '', assistant_response)
        messages.append({"role": "assistant", "content": assistant_response.replace("{{CREATE_SUPPORT_TICKET}}", ""), "message_time": localTime})
        
        table.update_item(
               Key={'conversationId': conversationId},
               UpdateExpression="SET messages = :messages",
               ExpressionAttributeValues={':messages': messages}
        )

        
        table.update_item(
               Key={'conversationId': conversationId},
               UpdateExpression="SET last_chat_time = :chat_time",
               ExpressionAttributeValues={':chat_time': formatted_time}
        )
        
        # print(get_openai_summary(messages))
        return {'response': messages}

    except Exception as e:
        error_table = dynamodb.Table(error_table_name)
        table = dynamodb.Table(table_name)

        conversationDetails = table.get_item(Key={'conversationId': conversationId})

        conversation = conversationDetails['Item']
        email_address = conversation.get('email')
        candidate_name = conversation.get('name')

        error_table.put_item(Item={
                        "createdAtPST":formatted_time, "conversationId":conversationId, "Email":email_address, "Name":candidate_name, "Error":f"Message Handling Error - {str(e)}"
                        })

        print(f"Error handling user message: {e}")
        print(traceback.format_exc())
        return {'error': str(e)}


# Lambda handler
def lambda_handler(event, context):
    try:
        data = json.loads(event['body'])
        if 'conversationId' in data:
            print(data,"test")
            # Handle existing conversation with a new message
            conversationId = data['conversationId']
            if 'localtime' in data:
                messageTime = data['localtime']
            else:
                messageTime = ''
            if 'message' in data:
                user_message = data['message']
            else:
                user_message = ''

            result = handle_user_message(conversationId, user_message, messageTime)
            if 'error' in result:
                return {
                    'statusCode': 400,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({'error': result['error']})
                }

            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({'response': result['response']})
            }

        else:
            try:
                # Handle initial request and create new conversation
                user_email = data.get('email')
                user_name = data.get('name')
                employer_name = data.get('emp_name')
                event_id = data.get('event_id', '')
                local_time_user = data.get('localtime')
                print(f"passed time is: {local_time_user}")
                # formatted_local_time = datetime.strptime(local_time_user, "%m/%d/%Y %I:%M:%S %p")
                # print(f"formated time is: {formatted_local_time}")
                if not user_email or not user_name:
                    return {
                        'statusCode': 400,
                        'headers': CORS_HEADERS,
                        'body': json.dumps({'error': 'Missing required fields: email or name.'})
                    }

                # Generate unique conversation ID
                conversationId = str(uuid.uuid4())

                # Initialize OpenAI client
                client = OpenAI(api_key=OPENAI_API_KEY)

                # Create a new thread
                thread = client.beta.threads.create()
                thread_id = thread.id  # Extract thread ID
            

                # Save user data in DynamoDB
                save_user_data(local_time_user, user_name, user_email, employer_name, event_id, conversationId, thread_id)
                print(f"New conversation created with ID: {conversationId} and OpenAI Thread ID: {thread_id}")

                return {
                    'statusCode': 200,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({'message': 'Conversation created.', 'conversationId': conversationId, 'message_time': local_time_user})
                }

            except Exception as e:
                error_table = dynamodb.Table(error_table_name)

                error_table.put_item(Item={
                    "createdAtPST":formatted_time, "conversationId":"No Id", "Email":"No Email", "Name":"No Name", "Error":f"No Parameters Error - {str(e)}"
                    })

                print('i am in No Parameters exception')
                return {
                    'statusCode': 500,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({'error': f"Request Body Error: {str(e)}"})
                }


    except ClientError as e:
        error_table = dynamodb.Table(error_table_name)
        
        error_table.put_item(Item={
            "createdAtPST":formatted_time, "conversationId":"No Id", "Email":"No Email", "Name":"No Name", "Error": f"AWS ClientError - {str(e)}"
            })
        print('i am in Except')

        print(f"AWS ClientError: {e}")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': f"AWS ClientError: {str(e)}"})
        }
    except Exception as e:
        error_table = dynamodb.Table(error_table_name)
        
        error_table.put_item(Item={
            "createdAtPST":formatted_time, "conversationId":"No Id", "Email":"No Email", "Name":"No Name", "Error": f"Unexpected Error - {str(e)}"
            })
        print('i am in Except')

        print(f"Unexpected Error: {e}")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': f"Unexpected Error: {str(e)}"})
        }

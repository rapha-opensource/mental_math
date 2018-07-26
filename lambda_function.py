"""
Mental Math Game

Intents:

play: poses an arithmetics problems for the level requested.
answer: checks the user answer and gives another problem of increasing difficulty.
        If checks fails, returns the score. If new score is greated than previous max, saves the new max on S3.
score: states the maximum score for the user (data is saved on S3)
"""

from random import choice, randrange
from math import floor
from functools import partial

from boto3 import client

s3 = client('s3')

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Welcome to Mental Math. " \
                    "Start a game by saying, " \
                    "new game"
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "Start a game by saying, " \
                    "new game"
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thank you for trying the Alexa Skills Kit sample. " \
                    "Have a nice day! "
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def generate_problem(level):
    pick = partial(randrange, start=1, stop=int(int(level)*'9'))
    a = pick()
    b = pick()
    c = a*b
    d = pick()
    e = pick()
    f = randrange(floor(.3*e*(a+d)))
    problem = f'what is {c} divided by {b}, plus {d}, times {e}, minus {f}?'
    expected_answer = (a+d)*e-f
    return problem, expected_answer
    
    
def new_game(intent, session, dialog_state):
    """
    Starts a game by setting the game state in the current session
    """
    card_title = intent['name']
    session_attributes = session.get('attributes', dict())
    session_attributes['score'] = 0

    if 'value' in intent['slots']['level']:
        level = intent['slots']['level']['value']
        problem, expected_answer = generate_problem(level)
        session_attributes.update({
            'problem': problem,
            'expected_answer': expected_answer,
            'level': level
        })
        speech_output = session_attributes['problem']
        reprompt_text = 'Say, new game at level 1'
    else:
        if dialog_state == 'STARTED':
            return delegateDialog(session)
        else:
            speech_output = "I'm not sure what you said. " \
                            "To start a new game say, new game"
            reprompt_text = 'Please, say, new game'
    return build_response(
        session_attributes,
        build_speechlet_response(
            card_title,
            speech_output,
            reprompt_text,
            False
        )
    )


congrats = (
    'Excellent!',
    'Great!',
    'Perfect answer.',
    'Very good.',
    'Nice',
    "Yeah, you cheated, but I'll accept that",
    "That's what she said.",
    "Hey! Don't use your cellphone, that's cheating!"
)

intro_new_problem = (
    'Ok, now, try this',
    'New problem',
    'Moving on',
    'Now, can you tell me the result of',
    'Since you are so good, what is the answer to'
)


wrong_intro = (
    'No, sorry',
    'Not quite',
    'Almost',
    'Not even close',
    'So close, but',
    'Sorry',
    'Nope',
    'That was a terrible answer',
    'hmm, try harder next time, okay?'
)

answer_intro = (
    'I was expecting',
    'the answer was',
    'the response was',
    'correct response was'
)


points = {
    '1': 10,
    '2': 100,
    '3': 1000
}


def check_answer(intent, session, dialog_state):
    """
    Check the answer provided by the user.
    If the answer is right, increment the score and enunciate another problem.
    If the answer is wrong, enunciate the correct answer and the score.
    
    """
    card_title = intent['name']
    session_attributes = session.get('attributes', dict())
    expected_answer = session_attributes.get('expected_answer', None)
    reprompt_text = None
    if not expected_answer:
        speech_output = 'Hmm, I need to give you a problem first. Say, new game'

    if 'value' in intent['slots']['answer']:
        answer = intent['slots']['answer']['value']
        try:
            answer = int(answer)
        except ValueError:
            pass
        if answer == expected_answer:
            level = session_attributes['level']
            problem, expected_answer = generate_problem(level)
            session_attributes.update({
                'problem': problem,
                'expected_answer': expected_answer,
                'score': session_attributes['score']+points[level]
            })
            speech_output = f'{choice(congrats)}. {choice(intro_new_problem)}: {problem} '
        else:
            speech_output = f'{choice(wrong_intro)}, ' \
                            f'{choice(answer_intro)} {expected_answer}. ' \
                            f'You scored: {session_attributes["score"]} points. ' \
                            'To start a new game, say: new game'
            session_attributes.update({
                'problem': None,
                'expected_answer': None,
                'score': 0
            })
    else:
        if dialog_state == 'STARTED':
            return delegateDialog(session)
        else:
            speech_output = "I'm not sure what you said. " \
                            "To provide an answer, say: the answer is 45"
            reprompt_text = 'Please, say, the answer is 23'
    return build_response(
        session_attributes,
        build_speechlet_response(
            card_title,
            speech_output,
            reprompt_text,
            False
        )
    )


def handle_fallback(session):
    print(f'session: {session}')
    if 'attributes' in session:
        attributes = session['attributes']
    else:
        attributes = None
    print(f'fallback attributes: {attributes}')
    if 'problem' in attributes:
        reprompt_text = 'Try to say: the answer is 12'
    else: 
        reprompt_text = 'Try to say: new game'
    return build_response(
        attributes,
        build_speechlet_response(
            'Say again?',
            'I did not understand what you said',
            reprompt_text,
            False
        )
    )

# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    intent = intent_request['intent']
    intent_name = intent['name']
    print(f'on_intent name={intent_name} requestId={intent_request["requestId"]}, sessionId={session["sessionId"]}') \

    # Dispatch to your skill's intent handlers
    if 'dialogState' in intent_request:
        dialog_state = intent_request['dialogState']
    else:
        dialog_state = None
    if intent_name == 'play':
        return new_game(intent, session, dialog_state)
    elif intent_name == 'provide_answer':
        return check_answer(intent, session, dialog_state)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    elif intent_name == "AMAZON.FallbackIntent":
        return handle_fallback(session)
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


def delegateDialog(session):
    response_body = {
        'version': '1.0',
        'sessionAttributes': session.get('attributes', None),
        'response': {
            'directives': [{ "type": "Dialog.Delegate" }],
            'shouldEndSession': False
            }
    }
    print(f'response body: {response_body}')
    return response_body

# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    session = event['session']
    print("event.session.application.applicationId=" +
          session['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")
    request = event['request']
    

    if session['new']:
        on_session_started(
            {
                'requestId': request['requestId']
            },
            session
        )

    if request['type'] == "LaunchRequest":
        return on_launch(request, session)
    elif request['type'] == "IntentRequest":
        return on_intent(request, session)
    elif request['type'] == "SessionEndedRequest":
        return on_session_ended(request, session)



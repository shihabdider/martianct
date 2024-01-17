import streamlit as st
from streamlit_chat import message
import requests
from requests.exceptions import HTTPError
import json
import urllib.parse
import os
from geopy.geocoders import Nominatim
import pandas as pd
from tenacity import retry, wait_random_exponential, stop_after_attempt 
import ClinicalTrialClasses as CT
import asyncio
import logging
import CTUtils as CTU

DEBUG=False
modelsAvailable=['GPT']

@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
async def generate_query_output(user_input="", model_to_use=""):
    output=""
    if user_input != "":
        output = await CTU.getResponseFromGPT(st.session_state['messages'])
            
        if (not output):
            output="Sorry I dont know the answer."
        return output          
  
    

#@st.cache_data breaks the way the controls function
def getNewData():
    st.session_state['refreshData'] = True
    st.session_state['condition']=st.session_state.condition_value
    st.session_state['treatment']=st.session_state.treatment_value
    st.session_state['location']=st.session_state.location_value
    st.session_state['other']=st.session_state.other_value
    st.session_state['studystatus']=st.session_state.studystatus_value
    st.session_state['model']=modelsAvailable.index(st.session_state.model_value)

def initializeSessionVariables():
    # Define default values for session variables
    default_values = {
        'homePageVisited': True,
        'refreshData': False,
        'refreshChat': False,
        'trials': None,
        'df': None,
        'json': "",
        'noOfStudies': 0,
        'recordsShown': 0,
        'generated': [],
        'past': [],
        'messages': [],
        'agent': None,
        'condition': "",
        'treatment': "",
        'location': "",
        'other': "",
        'studystatus': [],
        'model': 0,
    }

    # Set default values if not already in session_state
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Special handling for 'homePageVisited' and 'studyDetailPageVisited'
    if 'homePageVisited' not in st.session_state:
        if 'studyDetailPageVisited' in st.session_state:
            # Set refresh flags and clear messages if 'trials' is not None
            if st.session_state.get('trials') is not None:
                st.session_state['refreshData'] = True
                st.session_state['refreshChat'] = True
                st.session_state['messages'] = []

            # Delete 'studyDetailPageVisited' after handling
            del st.session_state['studyDetailPageVisited']



#@st.cache_data
def getNewChatResponse():
    st.session_state['refreshChat'] = True

@st.cache_data
def generate_system_prompt_gpt(data=""):
    return [
        {"role":"system",
         "content": f"""You are an AI assistant that answers questions on
         Clinical trials information provided as json below:
            {data}                
            """
         }
    ]
 

#endregion

async def main():

    st.set_page_config(page_title="MartianCT",  page_icon="public/martian_trials_icon.png", layout="wide")
    CTU.hideStreamlitStyle()
    
    #Init Logger
    CTU.init_logger()
   
    #region Begin Main UI Code
    initializeSessionVariables()

    #region ---- SIDEBAR ----
    st.sidebar.header("Filter on:")
    condition=st.sidebar.text_input("Condition or Disease",
                                    value=f"{st.session_state['condition']}",
                                    placeholder="Example: Ovarian Cancer",
                                    on_change=getNewData,
                                    key="condition_value")
    treatment=st.sidebar.text_input("Treament/Intervention",
                                    value=f"{st.session_state['treatment']}",
                                    placeholder="Example: BLU-222",
                                    on_change=getNewData,
                                    key="treatment_value")
    location=st.sidebar.text_input("Location (City)",
                                   value=f"{st.session_state['location']}",
                                   placeholder="Example: New York City",
                                   on_change=getNewData, key="location_value")
    other=st.sidebar.text_input("Other terms",
                                value=f"{st.session_state['other']}",
                                placeholder="Example: CCNE1",
                                on_change=getNewData, key="other_value")

    studyStatus=st.sidebar.multiselect("Status", ['ACTIVE_NOT_RECRUITING',
                                                  'COMPLETED',
                                                  'ENROLLING_BY_INVITATION',
                                                  'NOT_YET_RECRUITING',
                                                  'RECRUITING', 'SUSPENDED',
                                                  'TERMINATED', 'WITHDRAWN'
                                                  'AVAILABLE','NO_LONGER_AVAILABLE',
                                                  'TEMPORARILY_NOT_AVAILABLE',
                                                  'APPROVED_FOR_MARKETING','WITHHELD','UNKNOWN'],
                                       default=st.session_state['studystatus'],
                                       on_change=getNewData,
                                       key="studystatus_value")
    modelToUse=st.sidebar.selectbox("Model", modelsAvailable,
                                    on_change=getNewData,
                                    index=st.session_state['model'],
                                    key="model_value")

    search=st.sidebar.button("Submit")

    #endregion------END of SIDEBAR ----

    #region-----MAIN WINDOW--------

    st.markdown("# ![MartianCT](https://i.imgur.com/lUokwSa.png) MartianCT", unsafe_allow_html=True)

    #region container
    container=st.container()
    with container:
        if condition or treatment or location or studyStatus or other:
            pass
        else:
            st.markdown("## Welcome!")
            st.markdown("I can help you filter and explore clinical trials from [ClinicalTrials.gov](https://clinicaltrials.gov/).")
            st.markdown("Use the sidebar to filter on condition, treatment, location, status and keywords. You can then ask me questions about the results.")

    if search or st.session_state['refreshData']:
        trials=CT.Trials(CT.TrialsQuery(condition, treatment, location, studyStatus, other))
        await asyncio.create_task(trials.getStudies())

        st.session_state['trials']=trials
        st.session_state['df']=trials.getStudiesAsDF()
        try:
            st.session_state['json']=trials.getStudiesAsJson()
        except:
            pass
        
        st.session_state['refreshData']=False
        st.session_state['noOfStudies']=trials.totalCount
        st.session_state['recordsShown']=len(trials.studies)
        st.session_state['generated'] = []
        st.session_state['past'] = []
        st.session_state['messages']=[]

        
        st.session_state['messages']=generate_system_prompt_gpt(st.session_state['json'])

        with container:
            l, r = st.columns([.3,.8])
            with l:
                st.metric("No. of Studies", st.session_state['noOfStudies'])
            with r:
                st.metric("Records Shown", st.session_state['recordsShown']) 
    
        
    if not st.session_state['trials'] is None:
        st.session_state['df']=st.session_state['trials'].getStudiesAsDF()
        try: 
            st.session_state['json']=st.session_state['trials'].getStudiesAsJson()
        except:
            pass
        with container:

            st.dataframe(data=st.session_state['df'], use_container_width=True, hide_index=True)
    
        #end of UI and start of chat block
        st.info("What would you like to know about these trials?")
            
        # container for chat history
        response_container = st.container()
        # container for text box
        text_container = st.container()

        with text_container:
            with st.form(key='my_form', clear_on_submit=True):
                user_input = st.text_area("You:", key='input_home', height=100)
                submit_button = st.form_submit_button(label='Send')
                clear_button = st.form_submit_button(label="Clear Conversation")


            if (submit_button or st.session_state['refreshChat']) and user_input:
                with response_container:

                    #Append the user input
                    st.session_state['past'].append(user_input)
                    st.session_state['messages'].append({"role": "user", "content": user_input})
                    
                    with st.spinner('Sure! One second...'):
                        try: 
                            #this is still a blocking call. In the future if we do many queries we can do the gather pattern
                            output=await asyncio.create_task(generate_query_output(user_input, str(modelToUse)))

                           
                        except Exception as e:
                            output="Sorry I dont know the answer to that"

                        #Append the out from model
                        st.session_state['generated'].append(output)
                    
                        st.session_state['messages'].append({"role": "assistant", "content": output})       
                        st.session_state['refreshChat']=False

                # reset everything
            if clear_button:
                st.session_state['generated'] = []
                st.session_state['past'] = []
                st.session_state['messages'] = []
                if modelToUse=='GPT':
                    st.session_state['messages']=generate_system_prompt_gpt(st.session_state['json'])

            if st.session_state['generated']:
                with response_container:
                    for i in range(len(st.session_state['generated'])):
                        message(st.session_state["past"][i], is_user=True, key=str(i) + '_user', logo="https://t3.ftcdn.net/jpg/05/53/79/60/360_F_553796090_XHrE6R9jwmBJUMo9HKl41hyHJ5gqt9oz.jpg")
                        message(st.session_state["generated"][i], key=str(i), logo="https://i.imgur.com/lUokwSa.png", )


            
    #end of UI for pulling data from clinicaltrials.gov
    #endregion----End Main Window
    #endregion -- End UI Code

if __name__=="__main__":
        asyncio.run(main())

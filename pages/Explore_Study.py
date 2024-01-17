import streamlit as st
from streamlit.source_util import get_pages
import ClinicalTrialClasses as CT
import CTUtils as CTU
import asyncio
import openai
from streamlit_chat import message
import os
import logging


def clearOnChange():
    st.session_state['refreshChat'] = True

def setStudyID():
    st.session_state['studyID']=st.session_state['study']


def generate_system_prompt_gpt(data=""):
    return [{"role":"system","content": f"""You are an AI assistant that answers questions about clinical trials provided as json below:
                {data}                
                """}]


async def generate_study_detail_output(user_input=""):
    return await CTU.getResponseFromGPT(st.session_state['messages_study_detail'])
    
def initializeSessionVariables():
     #region Session State
    if 'studyDetailPageVisited' not in st.session_state:
        if 'homePageVisited' in st.session_state:
            if 'refreshChat' in st.session_state:
                st.session_state['refreshChat']=True

            #delete studyDetailPageVisited
            del st.session_state['homePageVisited']
        
        #create the fact they visited
        st.session_state['studyDetailPageVisited']=True

    if 'messages_study_detail' not in st.session_state:
        st.session_state['messages_study_detail'] =[]
    if 'df' not in st.session_state:
        st.session_state['df']=None
    if 'json' not in st.session_state:
        st.session_state['json']=None
    if 'generated_study_detail' not in st.session_state:
        st.session_state['generated_study_detail'] = []
    if 'past_study_detail' not in st.session_state:
        st.session_state['past_study_detail'] = []
    if 'refreshChat' not in st.session_state:
        st.session_state['refreshChat'] = False
    if 'studyID' not in st.session_state:
        st.session_state['studyID']=""
    
    #endregion

    
          
async def main():
    st.set_page_config(page_title="MartianCT",  page_icon="public/martian_trials_icon.png", layout="wide")
    CTU.hideStreamlitStyle()
    st.markdown("# ![MartianCT](https://i.imgur.com/lUokwSa.png) MartianCT", unsafe_allow_html=True)

    initializeSessionVariables()
    
    with st.sidebar:
        if st.session_state['df'] is not None:
            study=st.selectbox("Select Study ", 
                                list(st.session_state['df']['Nctid']),
                                   index=0,
                                   on_change=clearOnChange)
            
            st.divider()
        else: 
            study=st.text_input("Trial Identifier (NCTID)", 
                                    placeholder="Example: NCTID", value=st.session_state['studyID'], 
                                    on_change=setStudyID, key="study")
            get_study= st.sidebar.button(label='Fetch')
            
        
    #main form
    if study == "":
        st.info("Enter a NCTID in the sidebar to retrive trial data.", icon="ℹ️")
    else:
        if st.session_state['refreshChat']:
            st.session_state['generated_study_detail'] = []
            st.session_state['past_study_detail'] = []
            st.session_state['messages_study_detail'] = []
            url=CT.TrialsQuery(study_id=str(study)).getStudyDetailQuery()
            r=CTU.getQueryResultsFromCTGov(url)
            
            if r.status_code == 200:
                studyDetail=CT.StudyDetail(r.json())
                await studyDetail.getStudyDetail()
                st.session_state['json']=studyDetail.getStudyDetailsJson()
                st.session_state['messages_study_detail']=generate_system_prompt_gpt(st.session_state['json'])
            st.session_state['refreshChat']=False

        if (st.session_state['df'] is not None) or study != "": 
            studyDetail=st.session_state['json']
            st.subheader(f"{study}")
            print(studyDetail)
            st.markdown(f"**{studyDetail['briefTitle']}**")
            st.markdown(f"{studyDetail['briefSummary']}")
            st.info("What would you like to know about this study?")
            if studyDetail['pubmedArticles'] is not None:
                with st.expander(f"Associated PubMed Articles: {len(studyDetail['pubmedArticles'])}", expanded=False):
                    for article in studyDetail['pubmedArticles']:
                        st.info(f"""
                        [{article['title']}](https://pubmed.ncbi.nlm.nih.gov/{article['pubmed_id']}/)\n\n**PubMed ID:** {article['pubmed_id']}  
                        **Published:** {article['publication_date']}  
                        **Abstract:**  {article['abstract']}  
                        **Methods:**  {article['methods']}  
                        **Results:**  {article['results']}  
                        **Conclusions:**  {article['conclusions']}
                        """)
                                    
                
            # container for chat history
            response_container = st.container()
            # container for text box
            container = st.container()

            with container:
                with st.form(key='my_form', clear_on_submit=True):
                    user_input = st.text_area("You:", key='input', height=100)
                    submit_button = st.form_submit_button(label='Send')
                    clear_button = st.form_submit_button(label="Clear Conversation")


                if submit_button and user_input:
                    with response_container:
                        #Append the user input
                        st.session_state['past_study_detail'].append(user_input)
                        st.session_state['messages_study_detail'].append({"role": "user", "content": user_input})
                        with st.spinner('Sure! One second...'):
                            try: 
                                output=await generate_study_detail_output(user_input)
                            except Exception as e:
                                output="Sorry I dont know the answer to that."

                            #Append the out from model
                            st.session_state['generated_study_detail'].append(output)
                            st.session_state['messages_study_detail'].append({"role": "assistant", "content": output}) 
                            st.session_state['refreshChat']=False

                if clear_button:
                    st.session_state['generated_study_detail'] = []
                    st.session_state['past_study_detail'] = []
                    st.session_state['messages_study_detail'] = []
                    st.session_state['messages_study_detail']=generate_system_prompt_gpt(st.session_state['json'])

                if st.session_state['generated_study_detail']:
                    with response_container:
                        for i in range(len(st.session_state['generated_study_detail'])):
                            message(st.session_state["past_study_detail"][i], is_user=True, key=str(i) + '_user', logo="https://t3.ftcdn.net/jpg/05/53/79/60/360_F_553796090_XHrE6R9jwmBJUMo9HKl41hyHJ5gqt9oz.jpg")
                            message(st.session_state["generated_study_detail"][i], key=str(i), logo="https://i.imgur.com/lUokwSa.png", )
                

if __name__=="__main__":
    asyncio.run(main())

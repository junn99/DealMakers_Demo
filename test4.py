import os
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

# Define question categories and their questions
QUESTIONS = {
    "제품 개발 관련 질문": [
        "주름 개선과 수분 공급에 적합한 성분을 추천할 수 있나요?",
        "일본 및 북미 시장 규제를 충족하는 포뮬라 개발 경험이 있나요?",
        "자연 유래 성분 기반의 제품 개발이 가능한지, 비슷한 사례를 공유할 수 있나요?"
    ],
    "제품 사용감 및 품질 테스트": [
        "산뜻하고 부드러운 발림성을 구현할 수 있는 텍스처 개발이 가능한가요?",
        "주름 개선 테스트 결과를 제공하거나 인증 데이터를 생성할 수 있나요?",
        "내부 소비자 테스트 또는 샘플 평가를 지원할 수 있나요?"
    ]
}

# Initialize model
model = ChatOpenAI(model='gpt-4o')

def get_ai_response(answer: str) -> str:
    """Get AI response for the user's answer"""
    messages = [
        HumanMessage(content=f"브랜드사 입장에서 친절하게 답변해주세요.: {answer}")
    ]
    ai_response = model.invoke(messages)
    return ai_response.content

def get_negotiation_response(user_input: str, negotiation_state: dict) -> str:
    """Get AI response for MOQ negotiation as brand side"""
    target_moq = 1000
    current_moq = negotiation_state.get('current_moq', 3000)  # 제조사가 제시한 MOQ
    
    messages = [
        HumanMessage(content=f"""
            당신은 브랜드사의 담당자입니다. 제조사와 MOQ 협상을 진행중입니다.
            - 목표 MOQ: {target_moq}개
            - 제조사 제시 MOQ: {current_moq}개
            - 협상 전략: 
              1. 스타트업이라 초기 물량이 적다는 점을 강조
              2. 다음과 같은 조건들을 제안할 수 있음:
                 - 장기 계약 가능성 제시
                 - 정기 발주 약속 가능
                 - 초도 물량 이후 증량 계획 제시
                 - 선결제 또는 계약금 선지급 가능
              3. 제품 품질에 대한 테스트 필요성 언급
              4. 시장 반응을 보며 물량 확대 가능성 강조
              5. 경쟁사 언급하며 협상
            
            제조사 메시지: {user_input}
            """)
    ]
    ai_response = model.invoke(messages)
    return ai_response.content

def calculate_total_questions():
    """Calculate total number of questions across all categories"""
    return sum(len(questions) for questions in QUESTIONS.values())

def calculate_progress(state):
    """Calculate current progress"""
    total_done = 0
    for category, questions in QUESTIONS.items():
        if category in state['answers']:
            total_done += len(state['answers'][category])
    return total_done, calculate_total_questions()

def display_progress(state):
    """Display progress in main content area"""
    # Calculate progress
    questions_done, total_questions = calculate_progress(state)
    progress = questions_done / total_questions if total_questions > 0 else 0
    
    # Create three columns for progress display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("전체 진행률", f"{int(progress * 100)}%")
    with col2:
        st.metric("답변 완료", f"{questions_done}개")
    with col3:
        st.metric("남은 질문", f"{total_questions - questions_done}개")
    
    # Display overall progress bar
    st.progress(progress)
    
    # Show category-wise progress
    st.markdown("### 카테고리별 진행 상황")
    for category in QUESTIONS.keys():
        category_total = len(QUESTIONS[category])
        category_done = len(state['answers'].get(category, {}))
        category_progress = category_done / category_total
        
        st.write(f"**{category}**")
        st.progress(category_progress)
        st.write(f"{category_done}/{category_total} 완료")

def display_sidebar_answers(state):
    """Display category-wise answers in sidebar"""
    with st.sidebar:
        st.header("카테고리별 답변 보기")
        
        # Add category selector in sidebar
        categories = list(QUESTIONS.keys())
        selected_category = st.selectbox(
            "카테고리 선택",
            ["전체 보기"] + categories
        )
        
        if selected_category == "전체 보기":
            for category in categories:
                if category in state['answers'] and state['answers'][category]:
                    st.markdown(f"### {category}")
                    with st.expander(f"{category} 답변 보기"):
                        for q, a in state['answers'][category].items():
                            st.markdown(f"**Q:** {q}")
                            st.markdown(f"**A:** {a}")
                            if category in state['ai_responses'] and q in state['ai_responses'][category]:
                                st.markdown(f"**AI:** {state['ai_responses'][category][q]}")
                            st.markdown("---")
        else:
            if selected_category in state['answers'] and state['answers'][selected_category]:
                for q, a in state['answers'][selected_category].items():
                    st.markdown(f"**Q:** {q}")
                    st.markdown(f"**A:** {a}")
                    if selected_category in state['ai_responses'] and q in state['ai_responses'][selected_category]:
                        st.markdown(f"**AI:** {state['ai_responses'][selected_category][q]}")
                    st.markdown("---")

def main():
    st.title('OEM/ODM 제조사 상담 질문지')
    
    # Initialize session state
    if 'state' not in st.session_state:
        st.session_state.state = {
            'current_category': list(QUESTIONS.keys())[0],
            'current_question_idx': 0,
            'answers': {},
            'ai_responses': {},
            'waiting_for_approval': False,
            'current_answer': None
        }
    
    state = st.session_state.state
    
    # Display progress in main content
    display_progress(state)
    
    # Add separation line
    st.markdown("---")
    
    # Display answers in sidebar
    display_sidebar_answers(state)
    
    # Check if all questions are completed
    total_questions = calculate_total_questions()
    answered_questions = sum(len(answers) for answers in state['answers'].values())
    
    if answered_questions < total_questions:
        # Display current category and question
        current_category = state['current_category']
        current_idx = state['current_question_idx']
        
        if current_category in QUESTIONS and current_idx < len(QUESTIONS[current_category]):
            current_question = QUESTIONS[current_category][current_idx]
            
            st.subheader(f"현재 카테고리: {current_category}")
            st.write(f"현재 질문: {current_question}")
            
            # If we're not waiting for approval, show answer input
            if not state['waiting_for_approval']:
                answer = st.text_area("답변을 입력해주세요:", key=f"answer_{current_category}_{current_idx}")
                
                if st.button("답변 제출"):
                    state['current_answer'] = answer
                    state['waiting_for_approval'] = True
                    st.rerun()
            
            # If we are waiting for approval, show the confirmation dialog
            if state['waiting_for_approval']:
                st.write("---")
                st.write("다음 질문으로 넘어가시겠습니까?")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Yes"):
                        # Save the answer
                        if current_category not in state['answers']:
                            state['answers'][current_category] = {}
                        state['answers'][current_category][current_question] = state['current_answer']
                        
                        # Move to next question
                        if current_idx < len(QUESTIONS[current_category]) - 1:
                            state['current_question_idx'] += 1
                        else:
                            # Move to next category
                            categories = list(QUESTIONS.keys())
                            current_category_idx = categories.index(current_category)
                            if current_category_idx < len(categories) - 1:
                                state['current_category'] = categories[current_category_idx + 1]
                                state['current_question_idx'] = 0
                        
                        # Reset approval state
                        state['waiting_for_approval'] = False
                        state['current_answer'] = None
                        st.rerun()
                
                with col2:
                    if st.button("No"):
                        # Get and show AI response
                        ai_response = get_ai_response(state['current_answer'])
                        
                        # Save responses
                        if current_category not in state['ai_responses']:
                            state['ai_responses'][current_category] = {}
                        state['ai_responses'][current_category][current_question] = ai_response
                        
                        # Display conversation
                        st.write("---")
                        chat_container = st.container()
                        with chat_container:
                            st.markdown("""
                            <div style='background-color: #e6f3ff; padding: 10px; border-radius: 10px; margin-bottom: 10px;'>
                                <strong>고객님:</strong><br>
                                {}
                            </div>
                            """.format(state['current_answer']), unsafe_allow_html=True)
                            
                            st.markdown("""
                            <div style='background-color: #f0f0f0; padding: 10px; border-radius: 10px; margin-bottom: 10px;'>
                                <strong>상담원 AI:</strong><br>
                                {}
                            </div>
                            """.format(ai_response), unsafe_allow_html=True)
                        
                        # Reset approval state but keep current question
                        state['waiting_for_approval'] = False
                        state['current_answer'] = None
                        st.rerun()
    else:
        # All questions completed, start MOQ negotiation
        st.success("모든 질문이 완료되었습니다!")
        st.markdown("---")
        st.header("📊 MOQ 협상")
        
        # Initialize negotiation state
        if 'negotiation_state' not in st.session_state:
            st.session_state.negotiation_state = {
                'chat_history': [],
                'current_moq': 3000,
                'negotiation_complete': False
            }
        
        # Display chat history
        for message in st.session_state.negotiation_state['chat_history']:
            if message["role"] == "assistant":
                st.markdown("""
                <div style='background-color: #e6f3ff; padding: 10px; border-radius: 10px; margin-bottom: 10px;'>
                    <strong>브랜드사 담당자:</strong><br>
                    {}
                </div>
                """.format(message["content"]), unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style='background-color: #f0f0f0; padding: 10px; border-radius: 10px; margin-bottom: 10px;'>
                    <strong>제조사:</strong><br>
                    {}
                </div>
                """.format(message["content"]), unsafe_allow_html=True)
        
        # Initial message if chat history is empty
        if not st.session_state.negotiation_state['chat_history']:
            initial_message = """
            안녕하세요! 지금부터 MOQ 협상을 진행하고자 합니다.
            저희는 신생 브랜드이고, 초기 시장 진입 단계라 물량을 1,000개 정도로 시작하고 싶습니다.
            시장 반응을 보면서 물량을 늘려갈 계획이 있는데, 초기 MOQ 조정이 가능할까요?
            """
            st.session_state.negotiation_state['chat_history'].append({
                "role": "assistant",
                "content": initial_message
            })
            st.rerun()
        
        # Chat input
        user_input = st.text_input("제조사 답변을 입력하세요:", key="negotiation_input")
        
        if st.button("메시지 보내기") and user_input:
            # Add manufacturer message to chat history
            st.session_state.negotiation_state['chat_history'].append({
                "role": "user",
                "content": user_input
            })
            
            # Get AI response as brand
            ai_response = get_negotiation_response(
                user_input,
                st.session_state.negotiation_state
            )
            
            # Add AI response to chat history
            st.session_state.negotiation_state['chat_history'].append({
                "role": "assistant",
                "content": ai_response
            })
            
            st.rerun()
            
        # Option to end negotiation
        if st.button("협상 종료"):
            st.session_state.negotiation_state['negotiation_complete'] = True
            st.success("MOQ 협상이 종료되었습니다.")

if __name__ == "__main__":
    main()
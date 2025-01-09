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
        "자연 유래 성분 기반의 제품 개발이 가능한지, 비슷한 사례를 공유할 수 있나요?",
    ],
    "제품 사용감 및 품질 테스트": [
        "산뜻하고 부드러운 발림성을 구현할 수 있는 텍스처 개발이 가능한가요?",
        "주름 개선 테스트 결과를 제공하거나 인증 데이터를 생성할 수 있나요?",
        "내부 소비자 테스트 또는 샘플 평가를 지원할 수 있나요?",
    ],
}

# Initialize model
model = ChatOpenAI(model="gpt-4o", temperature=1)


def get_ai_response(answer: str) -> str:
    """Get AI response for the user's answer"""
    messages = [
        HumanMessage(content=f"브랜드사 입장에서 친절하게 답변해주세요.: {answer}")
    ]
    ai_response = model.invoke(messages)
    return ai_response.content


def get_negotiation_response(
    user_input: str, proposed_moq: int, chat_history: list
) -> str:
    """Get AI response for MOQ negotiation as brand side"""
    target_moq = 1000  # 브랜드사 목표 MOQ 고정

    # 이전 대화 내용을 문자열로 변환
    conversation_history = "\n".join(
        [
            f"{'브랜드사' if msg['role'] == 'assistant' else '제조사'}: {msg['content']}"
            for msg in chat_history
        ]
    )

    messages = [
        HumanMessage(
            content=f"""
            당신은 브랜드사의 협상가입니다.
            친절하고 자연스럽게 답변하세요.
            목표 MOQ {target_moq}개를 달성하기 위해서 제조사의 {proposed_moq}개와와 조정 중입니다.
            
            이전 대화 내용:
            {conversation_history}
            
            제조사 메시지: {user_input}
            """
        )
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
        if category in state["answers"]:
            total_done += len(state["answers"][category])
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
        category_done = len(state["answers"].get(category, {}))
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
        selected_category = st.selectbox("카테고리 선택", ["전체 보기"] + categories)

        if selected_category == "전체 보기":
            for category in categories:
                if category in state["answers"] and state["answers"][category]:
                    st.markdown(f"### {category}")
                    with st.expander(f"{category} 답변 보기"):
                        for q, a in state["answers"][category].items():
                            st.markdown(f"**Q:** {q}")
                            st.markdown(f"**A:** {a}")
                            if (
                                category in state["ai_responses"]
                                and q in state["ai_responses"][category]
                            ):
                                st.markdown(
                                    f"**AI:** {state['ai_responses'][category][q]}"
                                )
                            st.markdown("---")
        else:
            if (
                selected_category in state["answers"]
                and state["answers"][selected_category]
            ):
                for q, a in state["answers"][selected_category].items():
                    st.markdown(f"**Q:** {q}")
                    st.markdown(f"**A:** {a}")
                    if (
                        selected_category in state["ai_responses"]
                        and q in state["ai_responses"][selected_category]
                    ):
                        st.markdown(
                            f"**AI:** {state['ai_responses'][selected_category][q]}"
                        )
                    st.markdown("---")


def main():
    st.title("OEM/ODM 제조사 상담 질문지")

    # Initialize session state
    if "state" not in st.session_state:
        st.session_state.state = {
            "current_category": list(QUESTIONS.keys())[0],
            "current_question_idx": 0,
            "answers": {},
            "ai_responses": {},
            "waiting_for_approval": False,
            "current_answer": None,
            "proposed_moq": None,
            "chat_history": [],
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
    answered_questions = sum(len(answers) for answers in state["answers"].values())

    if answered_questions < total_questions:
        # Display current category and question
        current_category = state["current_category"]
        current_idx = state["current_question_idx"]

        if current_category in QUESTIONS and current_idx < len(
            QUESTIONS[current_category]
        ):
            current_question = QUESTIONS[current_category][current_idx]

            st.subheader(f"현재 카테고리: {current_category}")
            st.write(f"현재 질문: {current_question}")

            # If we're not waiting for approval, show answer input
            if not state["waiting_for_approval"]:
                answer = st.text_area(
                    "답변을 입력해주세요:",
                    key=f"answer_{current_category}_{current_idx}",
                )

                if st.button("답변 제출"):
                    state["current_answer"] = answer
                    state["waiting_for_approval"] = True
                    st.rerun()

            # If we are waiting for approval, show the confirmation dialog
            if state["waiting_for_approval"]:
                st.write("---")
                st.write("다음 질문으로 넘어가시겠습니까?")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Yes"):
                        # Save the answer
                        if current_category not in state["answers"]:
                            state["answers"][current_category] = {}
                        state["answers"][current_category][current_question] = state[
                            "current_answer"
                        ]

                        # Move to next question
                        if current_idx < len(QUESTIONS[current_category]) - 1:
                            state["current_question_idx"] += 1
                        else:
                            # Move to next category
                            categories = list(QUESTIONS.keys())
                            current_category_idx = categories.index(current_category)
                            if current_category_idx < len(categories) - 1:
                                state["current_category"] = categories[
                                    current_category_idx + 1
                                ]
                                state["current_question_idx"] = 0

                        # Reset approval state
                        state["waiting_for_approval"] = False
                        state["current_answer"] = None
                        st.rerun()

                with col2:
                    if st.button("No"):
                        # Get and show AI response
                        ai_response = get_ai_response(state["current_answer"])

                        # Save responses
                        if current_category not in state["ai_responses"]:
                            state["ai_responses"][current_category] = {}
                        state["ai_responses"][current_category][
                            current_question
                        ] = ai_response

                        # Display conversation
                        st.write("---")
                        chat_container = st.container()
                        with chat_container:
                            st.markdown(
                                """
                            <div style='background-color: #e6f3ff; padding: 10px; border-radius: 10px; margin-bottom: 10px;'>
                                <strong>고객님:</strong><br>
                                {}
                            </div>
                            """.format(
                                    state["current_answer"]
                                ),
                                unsafe_allow_html=True,
                            )

                            st.markdown(
                                """
                            <div style='background-color: #f0f0f0; padding: 10px; border-radius: 10px; margin-bottom: 10px;'>
                                <strong>상담원 AI:</strong><br>
                                {}
                            </div>
                            """.format(
                                    ai_response
                                ),
                                unsafe_allow_html=True,
                            )

                        # Reset approval state but keep current question
                        state["waiting_for_approval"] = False
                        state["current_answer"] = None
                        st.rerun()
    else:
        # All questions completed, start MOQ negotiation
        st.success("모든 질문이 완료되었습니다!")
        st.markdown("---")
        st.header("📊 MOQ 협상")

        # Get initial proposed MOQ if not set
        if state["proposed_moq"] is None:
            proposed_moq = st.number_input(
                "제조사의 제시 MOQ를 입력해주세요:", min_value=1000, step=100
            )
            if st.button("협상 시작"):
                state["proposed_moq"] = proposed_moq
                # Add initial message
                initial_message = f"""
                안녕하세요! 지금부터 MOQ 협상을 진행하고자 합니다.
                제조사측에서 제시하신 {state['proposed_moq']}개에서 조정이 가능할까요?
                """
                state["chat_history"].append(
                    {"role": "assistant", "content": initial_message}
                )
                st.rerun()

        # Continue negotiation
        if state["proposed_moq"] is not None:
            # Display chat history
            for message in state["chat_history"]:
                if message["role"] == "assistant":
                    st.markdown(
                        f"""
                    <div style='background-color: #e6f3ff; padding: 10px; border-radius: 10px; margin-bottom: 10px;'>
                        <strong>브랜드사 담당자:</strong><br>
                        {message["content"]}
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"""
                    <div style='background-color: #f0f0f0; padding: 10px; border-radius: 10px; margin-bottom: 10px;'>
                        <strong>제조사:</strong><br>
                        {message["content"]}
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

            # Chat input
            user_input = st.text_input(
                "제조사 답변을 입력하세요:", key="negotiation_input"
            )

            if st.button("메시지 보내기") and user_input:
                # Add manufacturer message to chat history
                state["chat_history"].append({"role": "user", "content": user_input})

                # Get AI response
                ai_response = get_negotiation_response(
                    user_input, state["proposed_moq"], state["chat_history"]
                )

                # Add AI response to chat history
                state["chat_history"].append(
                    {"role": "assistant", "content": ai_response}
                )

                st.rerun()

            # Option to end negotiation
            if st.button("협상 종료"):
                state["negotiation_complete"] = True
                st.success("MOQ 협상이 종료되었습니다.")


if __name__ == "__main__":
    main()

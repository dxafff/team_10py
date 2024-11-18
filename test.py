import streamlit as st
import google.generativeai as genai
import re
from PIL import Image

genai.configure(api_key="AIzaSyAOrYGN_AkLm9EvaeeeM4QEMhX6aLJNWLY")

SYSTEM_PROMPT = """Bạn là một chuyên gia nấu ăn chuyên nghiệp. Nhiệm vụ của bạn là:
1. Khi bắt đầu cuộc trò chuyện hoặc khi người dùng cần trợ giúp, hãy liệt kê các lựa chọn sau:
    1️⃣ Trắc nghiệm kiến thức nấu ăn
    2️⃣ Đề xuất công thức, thực đơn dựa trên sở thích, khẩu vị, và nguyên liệu có sẵn của người dùng
    3️⃣ Hướng dẫn kỹ thuật nấu ăn
    4️⃣ Gợi ý thực đơn
    5️⃣ Mẹo và thủ thuật nấu ăn
    6️⃣ Giải đáp thắc mắc về nấu ăn
    7️⃣ Cung cấp hướng dẫn từng bước chi tiết khi người dùng yêu cầu.
    8️⃣ Quản lý tủ lạnh và danh sách mua sắm
    9️⃣ Quản lý thông tin về nguyên liệu, khẩu vị, và giới hạn ăn uống của người dùng.
    🔟 Lập kế hoạch ăn uống hợp lý và cân bằng dinh dưỡng.

2. Khi được hỏi về lĩnh vực không liên quan đến nấu ăn, trả lời:
    "💡 Lĩnh vực này nằm ngoài chuyên môn của tôi, xin vui lòng hỏi những câu hỏi liên quan đến lĩnh vực nấu ăn" 
    và liệt kê lại các lựa chọn trên.

3. Khi người dùng chọn trắc nghiệm:
- Hiển thị cho người dùng:
    ====================
    📝 Câu hỏi: [Nội dung câu hỏi]

    A. [Đáp án A]
    B. [Đáp án B]
    C. [Đáp án C]
    D. [Đáp án D]
    ====================

- Đồng thời gửi kèm đáp án đúng trong một tin nhắn riêng biệt và ẩn, format như sau:
    ANSWER:[A/B/C/D]

4. Trả lời bằng ngôn ngữ phù hợp với người dùng (tiếng Việt, tiếng Anh, ...).

5. Khi người dùng trả lời:
- Nếu đúng: Hiển thị "✅ Chính xác!" và giải thích ngắn gọn.
- Nếu sai: Hiển thị "❌ Chưa chính xác. Đáp án đúng là [A/B/C/D]" và giải thích ngắn gọn.
- Sau đó tự động đưa ra câu hỏi mới."""


def init_session_state():
    if "chat" not in st.session_state:
        st.session_state.chat = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "quiz_score" not in st.session_state:
        st.session_state.quiz_score = 0
    if "current_question" not in st.session_state:
        st.session_state.current_question = None
    if "waiting_for_answer" not in st.session_state:
        st.session_state.waiting_for_answer = False
    if "correct_answer" not in st.session_state:
        st.session_state.correct_answer = None
    if "vision_model" not in st.session_state:
        st.session_state.vision_model = None


def extract_quiz_content(response_text):
    try:
        pattern = r"={2,}\n(.*?)\n={2,}"
        quiz_section = re.search(pattern, response_text, re.DOTALL)

        if not quiz_section:
            return None

        content = quiz_section.group(1).strip()

        question_match = re.search(r"📝 Câu hỏi: (.*?)(?=\n|$)", content)
        options_pattern = r"([A-D])\. (.*?)(?=\n[A-D]\.|$)"
        options = re.findall(options_pattern, content, re.DOTALL)

        answer_match = re.search(r"ANSWER:([A-D])", response_text)

        if not (question_match and options and answer_match):
            return None

        return {
            'question': question_match.group(1).strip(),
            'options': [opt[1].strip() for opt in options],
            'correct_answer': answer_match.group(1).strip()
        }
    except Exception as e:
        st.error(f"Error extracting quiz content: {str(e)}")
        return None


def display_quiz_interface(quiz_content):
    if not quiz_content:
        return None

    try:
        selected_answer = st.radio(
            f"📝 **Câu hỏi:** {quiz_content['question']}",
            ['A', 'B', 'C', 'D'],
            format_func=lambda x: f"{x}. {quiz_content['options'][ord(x) - ord('A')]}"
        )

        submit_button = st.button("Xác nhận đáp án", type="primary")
        if submit_button:
            return selected_answer

    except Exception as e:
        st.error(f"Error displaying quiz interface: {str(e)}")
    return None


def handle_quiz_answer(user_answer, correct_answer):
    try:
        if user_answer == correct_answer:
            st.session_state.quiz_score += 1
            st.success("✅ Chính xác!")
        else:
            st.error(f"❌ Chưa chính xác. Đáp án đúng là {correct_answer}")
        return True
    except Exception as e:
        st.error(f"Error handling quiz answer: {str(e)}")
        return False


def initialize_model(model_name="gemini-1.5-flash-002"):
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        return model
    except Exception as e:
        st.error(f"Error initializing model: {str(e)}")
        return None


def process_image(image, prompt):
    try:
        if st.session_state.vision_model is None:
            st.session_state.vision_model = initialize_model()

        if st.session_state.vision_model is None:
            return "Không thể khởi tạo model xử lý hình ảnh"

        response = st.session_state.vision_model.generate_content([
            prompt,
            image
        ])
        return response.text
    except Exception as e:
        return f"Lỗi khi xử lý hình ảnh: {str(e)}"


def reset_session():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 8192,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]


def main():
    st.set_page_config(
        page_title="👨‍🍳 Chuyên Gia Nấu Ăn AI",
        page_icon="👨‍🍳",
        layout="wide"
    )

    init_session_state()

    with st.sidebar:
        st.markdown("### 📘 Hướng dẫn sử dụng")
        st.markdown("""
        1. Chọn một trong các tùy chọn được liệt kê
        2. Với câu hỏi trắc nghiệm:
           - Chọn đáp án bằng cách click vào lựa chọn
           - Nhấn "Xác nhận đáp án" để kiểm tra
           - Xem giải thích và tiếp tục với câu hỏi tiếp theo
        3. Với các chức năng khác:
           - Nhập câu hỏi hoặc yêu cầu của bạn
           - Đợi phản hồi từ AI
        """)

        if st.button("🔄 Bắt đầu lại"):
            reset_session()

        if st.session_state.quiz_score > 0:
            st.markdown(f"### 🏆 Điểm số: {st.session_state.quiz_score}")

    st.title("👨‍🍳 Chuyên Gia Nấu Ăn AI")
    st.markdown("### 📷 Tải lên hình ảnh món ăn")
    uploaded_file = st.file_uploader("Chọn hình ảnh món ăn để phân tích", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Hình ảnh đã tải lên", use_column_width=True)

        analyze_button = st.button("Phân tích món ăn")
        if analyze_button:
            with st.spinner("Đang phân tích hình ảnh..."):
                prompt = """Hãy phân tích hình ảnh món ăn này và cung cấp thông tin sau:
                1. Tên món ăn (nếu nhận dạng được)
                2. Các thành phần chính có thể nhìn thấy
                3. Đánh giá về cách trình bày
                4. Gợi ý cải thiện (nếu có)
                5. Ước tính giá trị dinh dưỡng"""

                analysis = process_image(image, prompt)
                st.markdown("### 🔍 Kết quả phân tích")
                st.markdown(analysis)

                st.session_state.messages.extend([
                    {"role": "user", "content": "Phân tích hình ảnh món ăn"},
                    {"role": "assistant", "content": analysis}
                ])
    st.markdown("---")

    if st.session_state.chat is None:
        model = initialize_model()
        if model is not None:
            st.session_state.chat = model.start_chat(history=[])
            initial_response = st.session_state.chat.send_message(SYSTEM_PROMPT)
            st.session_state.messages = [{"role": "assistant", "content": initial_response.text}]

    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "📝 Câu hỏi:" in message["content"]:
                content_parts = message["content"].split("====================")
                non_quiz_content = content_parts[0].strip()
                if non_quiz_content:
                    st.markdown(non_quiz_content)

                quiz_content = extract_quiz_content(message["content"])
                if quiz_content and idx == len(st.session_state.messages) - 1:
                    st.session_state.current_question = quiz_content
                    st.session_state.waiting_for_answer = True
                    st.session_state.correct_answer = quiz_content['correct_answer']

                    user_answer = display_quiz_interface(quiz_content)
                    if user_answer:
                        if handle_quiz_answer(user_answer, quiz_content['correct_answer']):
                            response = st.session_state.chat.send_message(f"Tôi chọn đáp án {user_answer}")
                            st.session_state.messages.extend([
                                {"role": "user", "content": f"Tôi chọn đáp án {user_answer}"},
                                {"role": "assistant", "content": response.text}
                            ])
                            st.session_state.waiting_for_answer = False
                            st.rerun()
            else:
                visible_content = re.sub(r'ANSWER:[A-D]', '', message["content"]).strip()
                st.markdown(visible_content)

    if not st.session_state.waiting_for_answer:
        user_input = st.chat_input("Nhập câu hỏi của bạn...")

        if user_input:
            try:
                st.chat_message("user").markdown(user_input)
                st.session_state.messages.append({"role": "user", "content": user_input})

                response = st.session_state.chat.send_message(user_input)
                with st.chat_message("assistant"):
                    st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})

                st.rerun()

            except Exception as e:
                st.error(f"Có lỗi xảy ra: {str(e)}")


if __name__ == "__main__":
    main()
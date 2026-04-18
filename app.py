import streamlit as st

from utils import (
    extract_text,
    create_vector_store,
    extract_concepts
)

from agents import build_graph

# ------------------- PAGE -------------------

st.set_page_config(page_title="Aru - Autonomous Tutor", layout="wide")
st.title(" Autonomous Learning Agent with Feynman Technique")

# ------------------- SESSION -------------------

defaults = {
    "vectorstore": None,
    "concepts": [],
    "current_index": 0,
    "attempts": 0,
    "graph": build_graph(),

    "explanation": "",
    "question": "",
    "context": "",
    "evaluation": "",
    "correct_answer": "",
    "hint": "",
    "simplified_explanation": ""
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ------------------- UPLOAD -------------------

st.subheader("📄 Upload PDF")

file = st.file_uploader("Upload PDF", type="pdf")

if file:
    if st.button("Process Document", key="process_btn"):
        text = extract_text(file)

        st.session_state.vectorstore = create_vector_store(text)
        st.session_state.concepts = extract_concepts(text)

        st.success("Concepts Ready!")

# ------------------- CONCEPTS -------------------

if st.session_state.concepts:

    st.subheader("📚 Topics")

    for i, concept in enumerate(st.session_state.concepts):
        if st.button(concept, key=f"concept_{i}"):
            st.session_state.current_index = i
            st.session_state.attempts = 0

            # Reset everything
            st.session_state.explanation = ""
            st.session_state.question = ""
            st.session_state.evaluation = ""
            st.session_state.correct_answer = ""
            st.session_state.hint = ""
            st.session_state.simplified_explanation = ""

# ------------------- LEARNING -------------------

if st.session_state.concepts:

    idx = st.session_state.current_index

    if idx >= len(st.session_state.concepts):
        st.success("🎉 All topics completed!")
        st.stop()

    concept = st.session_state.concepts[idx]

    st.subheader(f"🧩 {concept}")

    # ------------------- EXPLAIN -------------------

    if st.button("Explain", key="explain_btn"):

        result = st.session_state.graph.invoke({
            "concept": concept,
            "vectorstore": st.session_state.vectorstore,
            "attempts": st.session_state.attempts,
            "answer": ""
        })

        st.session_state.explanation = result.get("explanation", "")
        st.session_state.question = result.get("question", "")
        st.session_state.context = result.get("context", "")

    if st.session_state.explanation:
        with st.expander("📖 Explanation"):
            st.write(st.session_state.explanation)

    # ------------------- QUESTION -------------------

    if st.session_state.question:

        st.subheader("❓ Question")
        st.write(st.session_state.question)

        answer = st.text_area("Your Answer", key="answer_box")

        if st.button("Submit Answer", key="submit_btn"):

            result = st.session_state.graph.invoke({
                "concept": concept,
                "vectorstore": st.session_state.vectorstore,
                "context": st.session_state.context,
                "answer": answer,
                "attempts": st.session_state.attempts
            })

            # Store results
            st.session_state.evaluation = result.get("evaluation", "")
            st.session_state.attempts = result.get("attempts", 0)
            st.session_state.hint = result.get("hint", "")
            st.session_state.simplified_explanation = result.get("simplified_explanation", "")

            decision = result.get("decision", "")

            # ------------------- SHOW EVALUATION -------------------

            st.subheader("📊 Evaluation")
            st.write(st.session_state.evaluation)

            # ------------------- 🔥 NEW PART (HINT + SIMPLIFY) -------------------

            if st.session_state.hint:
                st.info(f"💡 Hint: {st.session_state.hint}")

            if st.session_state.simplified_explanation:
                st.warning("🪶 Simplified Explanation")
                st.write(st.session_state.simplified_explanation)

            # ------------------- DECISION -------------------

            if decision == "next":
                st.success("✅ Moving to next concept")

                st.session_state.current_index += 1
                st.session_state.attempts = 0

                st.session_state.explanation = ""
                st.session_state.question = ""
                st.session_state.hint = ""
                st.session_state.simplified_explanation = ""

            elif decision == "fail":
                st.error("❌ Attempts over")

                st.session_state.correct_answer = result.get("correct_answer", "")

                with st.expander("✅ Correct Answer"):
                    st.write(st.session_state.correct_answer)

                st.session_state.current_index += 1
                st.session_state.attempts = 0

                st.session_state.explanation = ""
                st.session_state.question = ""
                st.session_state.hint = ""
                st.session_state.simplified_explanation = ""

            elif decision in ["hint", "simplify"]:
                st.warning("🔁 Try again")

    # ------------------- DEBUG -------------------

    with st.expander("🔍 Context"):
        st.write(st.session_state.context)

    # ------------------- PROGRESS -------------------

    progress = st.session_state.current_index / len(st.session_state.concepts)
    st.progress(progress)
import React, { useState, useEffect } from "react";
import { demoQuestions, maxturns } from "./Variables";
import Cookie from "./components/Cookie";
import DemoQ from "./components/DemoQ";
import Message from "./components/Message";

const App = () => {
  const [messageHis, setMessageHis] = useState([]);
  const [announcement, setAnnoucement] = useState(
    "You've unlocked a new feature! Ask me which party is closest to you.",
  );
  const [progressMsg, setProgressMsg] = useState("Knowledge Level");
  const [message, setMessage] = useState("");
  const [noInput, setNoInput] = useState(false);
  const [noSubmit, setNoSubmit] = useState(false);
  const [noDemo, setNoDemo] = useState(false);
  const [turns, setTurns] = useState(1);

  const csrftoken = Cookie("csrftoken");
  const queryParams = new URLSearchParams(window.location.search);

  const homeCountry = queryParams.get("home_country");
  const hostCountry = queryParams.get("host_country");
  const customQuestion = queryParams.get("custom_question");
  const userId = queryParams.get("user_id");

  const handleCreateMsg = (user, response) => {
    const key = messageHis.length;

    setMessageHis((prevMessages) => [
      ...prevMessages,
      {
        userMessage: user,
        aiMessage: response,
        key: key,
      },
    ]);
  };

  const refreshChat = () => {
    setNoInput(false);
    setNoSubmit(false);
    setMessage("");
  };

  const unlockPartyAlignmentPrediction = () => {
    document.getElementById("big-announcement").classList.remove("hidden");
  };

  const endChat = () => {
    const progressBar = document.getElementById("knowledge-level-bar");
    const progressTitle = document.getElementById("knowledge-level-text");
    const submitButton = document.getElementById("submit-button");
    const annoucement = document.getElementById("big-announcement");

    setNoInput(true);
    setNoSubmit(true);
    setMessage("Please move on to the next question.");
    setProgressMsg("Complete");
    setAnnoucement("Please move on to the next question.");

    progressBar.classList.remove("bg-[#a9b3f5]");
    annoucement.classList.remove("bg-second");
    annoucement.classList.add("text-white");
    progressBar.classList.add("bg-[#545c94]");
    progressTitle.classList.add("text-white");
    submitButton.classList.add("hidden");
    annoucement.classList.add("bg-second-dark");
  };

  const scrollToBottom = () => {
    const chatbotHistory = document.getElementById("chatbot-history");
    chatbotHistory.scrollTop = chatbotHistory.scrollHeight;
  };

  const updateProgressBar = () => {
    const progressBar = document.getElementById("knowledge-level-bar");
    const progressPercentage = Math.min((turns / maxturns) * 100, 100);
    progressBar.style.width = progressPercentage + "%";

    if (turns >= maxturns / 2) {
      unlockPartyAlignmentPrediction();
    }
  };

  const submitFunction = async (event) => {
    event.preventDefault();

    setNoInput(true);
    setNoSubmit(true);

    let historyItem = document.createElement("li");
    let userMessage = document.createElement("div");
    let messageInput = document.getElementById("message-input");

    userMessage.innerText = message;
    userMessage.className = "chatbot-history-user";
    historyItem.appendChild(userMessage);

    let botResponse = document.createElement("div");
    botResponse.innerText = "...";
    botResponse.className = "chatbot-history-response";
    historyItem.append(botResponse);

    let formData = new FormData();
    formData.append("user_id", userId);
    formData.append("message", message);
    formData.append("home_country", homeCountry);
    formData.append("host_country", hostCountry);

    setTurns((prevTruns) => prevTruns + 1);
    updateProgressBar();

    if (turns === maxturns / 2) {
      messageInput.placeholder = "Which party comes closest to my views?";
    }

    await fetch(`${process.env.REACT_APP_API_BASE_URL}/api/v1/query/two-countries`, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrftoken,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query: message,
        home_country: homeCountry,
        host_country: hostCountry,
        user_id: userId,
        top_k: 7,
      }),
    })
      .then((response) => {
        return response.json();
      })
      .then((data) => {
        const value = data.data.response;
        handleCreateMsg(message, value);
      })
      .then(() => {
        if (turns >= maxturns) {
          endChat();
        } else {
          refreshChat();
        }
      })
      .catch((error) => {
        console.error("Error: ", error);
      });
  };

  return (
    <div className="flex-col h-screen justify-between">
      <div id="chatbot-container" className="flex h-full flex-col-reverse">
        <div className="bg-shadow flex flex-col-reverse">
          <div
            id="knowledge-level-container"
            className="p-4 bg-gray-300 rounded"
          >
            <span id="knowledge-level-text" className="text-lg font-bold">
              {progressMsg}
            </span>
            <div
              id="knowledge-level-bar"
              className="w-0 h-6 bg-[#a9b3f5] rounded"
            />
          </div>

          <div
            id="big-announcement"
            className="hidden p-2 text-center text-lg font-bold bg-second rounded"
          >
            {announcement}
          </div>

          <form
            id="chatbot-form"
            className="flex p-2 bg-gray-200 rounded-t-lg"
            onSubmit={submitFunction}
          >
            <input
              id="message-input"
              type="text"
              disabled={noInput}
              value={message}
              className="flex-1 p-2 rounded bg-white"
              placeholder="Ask me about politics."
              onChange={(e) => {
                setMessage(e.target.value);
              }}
            />
            <button
              id="submit-button"
              type="submit"
              disabled={noSubmit}
              className="cursor-pointer ml-2 p-2 rounded bg-prim text-white font-semibold"
            >
              Ask
            </button>
          </form>
        </div>

        <ul id="chatbot-history" className="flex flex-col overflow-auto p-4">
          <div className="overflow-auto">
            {demoQuestions.map((question, index) => (
              <DemoQ
                key={index}
                isHidden={noDemo}
                text={question}
                setText={setMessage}
                setDisable={setNoDemo}
                homeCountry={homeCountry}
                hostCountry={hostCountry}
                customQuestion={customQuestion}
              />
            ))}
          </div>
          {messageHis.map((message) => (
            <Message
              key={message.key}
              userMessage={message.userMessage}
              aiMessage={message.aiMessage}
              scrollToBottom={scrollToBottom}
            />
          ))}
        </ul>
      </div>
    </div>
  );
};

export default App;

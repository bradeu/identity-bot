import React, { useState, useEffect } from "react";
import UserIcon from "../assets/UserIcon.png";
import RobotIcon from "../assets/RobotIcon.png";

const Message = ({ userMessage, aiMessage, scrollToBottom }) => {
    const [displayedMessage, setDisplayedMessage] = useState("");
    let speed = 5;

    const appendLetter = (letter) => {
        setDisplayedMessage((prev) => prev + letter);
    };

    useEffect(() => {
        console.log(aiMessage);

        let i = 0;
        const interval = setInterval(() => {
            if (i < aiMessage.length) {
                appendLetter(aiMessage[i]);
                scrollToBottom();
                i++;
            } else {
                clearInterval(interval);
            }
        }, speed);

        return () => clearInterval(interval);
    }, []);

    return (
        <div className="flex flex-col gap-2 my-2">
            <div className="flex flex-row justify-end items-end gap-2 font-semibold text-gray-600">
                <div className="message-blue">{userMessage}</div>
                <div className="bg-[#90cbef] p-2 ml-1 rounded-full">
                    <img src={UserIcon} className="w-8" />
                </div>
            </div>
            <div className="flex flex-row justify-start items-end gap-2 font-semibold text-gray-600">
                <div className="bg-[#bcbcbc] p-2 mr-1 rounded-full">
                    <img src={RobotIcon} className="w-8" />
                </div>
                <div className="message-orange">{displayedMessage}</div>
            </div>
        </div>
    );
};

export default Message;
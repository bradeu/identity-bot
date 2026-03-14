import React from "react";

const DemoQ = ({
    isHidden,
    text,
    setText,
    setDisable,
    homeCountry,
    customQuestion,
    hostCountry,
}) => {
    console.log(customQuestion);

    let displayText;
    displayText = text.replace("my country of origin", homeCountry);
    displayText = displayText.replace("policies I care about", customQuestion);
    displayText = displayText.replace("my current country", hostCountry);

    return (
        <>
            <button
                class={`demo-question bg-prim hover:bg-prim-hover text-white font-semibold rounded-full bg-shadow py-2 px-4 m-1 ${isHidden ? "hidden" : ""}`}
                onClick={() => {
                    setText(displayText);
                    setDisable(true);
                }}
            >
                {displayText}
            </button>
        </>
    );
};

export default DemoQ;
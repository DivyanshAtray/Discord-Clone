window.onload = () => {
    if (!getUsernameFromCookies()) {
        // Fetch username only if it's not already in cookies
        fetchAndSaveUsername();
    }
};
function getUsernameFromCookies() {
    const cookies = document.cookie.split(';'); // Split cookies by ";"
    for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim(); // Remove leading/trailing spaces
        if (cookie.startsWith('username=')) {
            return cookie.split('=')[1]; // Return the value of the username
        }
    }
    return null; // Return null if username is not found
}

async function fetchAndSaveUsername() {
    try {
        const response = await fetch('/get_username'); // Replace with your endpoint
        if (!response.ok) {
            throw new Error('Failed to fetch username');
        }
        const data = await response.json();
        if (data.username) {
            // Save username to cookies
            document.cookie = `username=${data.username}; path=/`; // Add ";path=/" to make it accessible site-wide
            console.log("Fetched and saved username in cookies:", data.username);
            return data.username; // Return the username if needed
        } else {
            console.error("Error:", data.error);
            return null;
        }
    } catch (error) {
        console.error("Error while fetching username:", error);
        return null;
    }
}
const inputField = document.getElementById("messageInput");
const sendButton = document.querySelector(".send");
const messagesContainer = document.querySelector(".messages");
const fileInput = document.getElementById("fileInput");
const attachmentButton = document.querySelector(".attachment");
const socket = io.connect();
let selectedFile = null;


socket.on('connect', function () { console.log("connected") });
socket.on('disconnect', function () { console.log("disconnected") });
function sendMessage() {
    const messageText = inputField.value.trim();

    // Check if there is no message text and no selected file, then return.
    if (messageText === "" && !selectedFile) return;

    const userMessageDiv = document.createElement("div");
    userMessageDiv.classList.add("message", "user-message");

    const formData = new FormData(); // Create FormData object for API request
    if (selectedFile) {
        formData.append("file", selectedFile);

        // Show file upload preview in the chat
        const fileURL = URL.createObjectURL(selectedFile);
        userMessageDiv.innerHTML = `<a href="${fileURL}" target="_blank">${selectedFile.name}</a>`;
        selectedFile = null;
    }

    if (messageText !== "") {
        console.log(messageText)
        formData.append("message", messageText); // Add message to FormData
        userMessageDiv.innerHTML += formatMessage(messageText); // Append message to chat
    }

    messagesContainer.appendChild(userMessageDiv);

    // Send the FormData to the API endpoint
    fetch("/send_message", {
        method: "POST",
        body: formData // FormData object includes both file and message
    }).then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Emit the socket event after the message is successfully sent
                const USER = getUsernameFromCookies();
                socket.emit("send_message", { message: messageText, username: USER });
            }
        });

    // Clear input field after sending
    inputField.value = "";
}


// Function to format messages (Bold, Italics, Code Blocks)
function formatMessage(text) {
    return text
        .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>") // Bold
        .replace(/#(.+?)#/g, "<h1>$1</h1>") // Heading
        .replace(/\*(.+?)\*/g, "<i>$1</i>") // Italics
        .replace(/```([\s\S]+?)```/g, (match, code) => `
    <div class="code-block" style="position: relative; display: inline-block;">
        <pre><code>${escapeHtml(code)}</code></pre>
        <button class="copy-btn" onclick="copyToClipboard(this)" 
            style="position: absolute; right: 5px; top: 5px; cursor: pointer;">📋</button>
    </div>
`);
}

// Function to copy code to clipboard
function copyToClipboard(button) {
    const codeBlock = button.previousElementSibling; // Get the <pre><code> block
    const code = codeBlock.textContent.trim();

    navigator.clipboard.writeText(code)
        .then(() => {
            button.textContent = "✔ Copied!";
            setTimeout(() => (button.textContent = "📋"), 2000);
        })
        .catch(err => console.error("Failed to copy:", err));
}

// Escape HTML to prevent injection
function escapeHtml(text) {
    return text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
}


function renderLatex() {
    if (window.MathJax) MathJax.typesetPromise();
}

function autoResizeTextarea(el) {
    el.style.height = "auto";
    el.style.height = el.scrollHeight + "px";
}

inputField.addEventListener("input", function () {
    autoResizeTextarea(this);
});

inputField.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

sendButton.addEventListener("click", sendMessage);

attachmentButton.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", function () {
    if (this.files.length > 0) {
        selectedFile = this.files[0];
        inputField.value = `📎 ${selectedFile.name}`;
        autoResizeTextarea(inputField);
    }
});

function downloadFile(url, filename) {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}


socket.on("broadcast_message", (data) => {
    // Automatically called when the server emits "broadcast_message"
    const USER = getUsernameFromCookies();

    const username = data.username || "Anonymous";
    const message = data.message || "";
    if (username == USER) {
    } else {
        const botMessageDiv = document.createElement("div");
        botMessageDiv.classList.add("message", "bot-message");
        botMessageDiv.innerHTML = formatMessage(message);
        messagesContainer.appendChild(botMessageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        renderLatex();
    }
});



document.addEventListener("DOMContentLoaded", function () {
    var openPopup = document.getElementById('openPopup');
    var popupOverlay = document.getElementById('popupOverlay');
    var popup = document.getElementById('popup');
    var sendButton = document.getElementById('sendButton');
    var friendIdInput = document.getElementById('friendIdInput');

    // Ensure popup is hidden on page load
    popupOverlay.style.display = 'none';

    // Show popup when clicking on the image
    openPopup.addEventListener('click', function () {
        popupOverlay.style.display = 'flex';
        friendIdInput.focus(); // Auto-focus input field
    });

    // Function to close popup
    function closePopup() {
        popupOverlay.style.display = 'none';
    }

    // Close popup when clicking outside the popup
    popupOverlay.addEventListener('click', function (event) {
        if (event.target === popupOverlay) {
            closePopup();
        }
    });

    // Close popup when clicking "Send" button
    sendButton.addEventListener('click', function () {
        closePopup();
    });

    // Prevent popup from closing when clicking inside it
    popup.addEventListener('click', function (event) {
        event.stopPropagation();
    });

    // Close popup when pressing Enter in input field
    friendIdInput.addEventListener('keypress', function (event) {
        if (event.key === 'Enter') {
            closePopup();
        }
    });
});




function sendMessage() {
    const messageText = inputField.value.trim();
    if (messageText === "" && !selectedFile) return;

    const userMessageDiv = document.createElement("div");
    userMessageDiv.classList.add("message", "user-message");

    if (messageText !== "") {
        userMessageDiv.innerHTML = formatMessage(messageText);
    }

    messagesContainer.appendChild(userMessageDiv);
    scrollToBottom(); // Auto-scroll after sending a message
    dataToSend= new FormData()
    dataToSend.append("message",messageText)
    fetch("/send_message", {
        method: "POST",
        body: dataToSend
    }).then(() => {
        const USER = getUsernameFromCookies();
        socket.emit("send_message", { message: messageText, username: USER });
    });

    inputField.value = ""; // Clear input field
    scrollToBottom();
}

document.addEventListener("DOMContentLoaded", () => {
    const sendButton = document.getElementById("sendButton");
    const friendIdInput = document.getElementById("friendIdInput");

    sendButton.addEventListener("click", async () => {
        const friendId = friendIdInput.value;

        if (!friendId) {
            alert("Please enter a valid Friend ID");
            return;
        }

        try {
            // Make an API call to fetch user information
            const response = await fetch(`/profile?id=${friendId}`);

            const data = await response.json();
            if (data[0]["username"]) {
                alert(`Friend request sent to ${data[0]["username"]}`);
            } else {
                alert("User does not exist with that ID");
            }

        } catch (error) {
            alert(`User does not exist with ID ${friendId}`);
        }
    });
});

socket.on("broadcast_message", (data) => {
    const USER = getUsernameFromCookies();
    const username = data.username || "Anonymous";
    const message = data.message || "";

    if (username !== USER) {
        const botMessageDiv = document.createElement("div");
        botMessageDiv.classList.add("message", "bot-message");
        botMessageDiv.innerHTML = formatMessage(message);
        messagesContainer.appendChild(botMessageDiv);

        scrollToBottom(); // Auto-scroll when receiving a message
        renderLatex();
    }
});


function scrollToBottom() {
    const messagesContainer = document.querySelector(".messages");
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}




document.addEventListener("DOMContentLoaded", function() {
var openRequestsPopup = document.querySelector('.icon_top[src="/static/inbox.svg"]');
var friendRequestsOverlay = document.getElementById('friendRequestsOverlay');
var closeRequestsPopup = document.getElementById('closeRequestsPopup');

friendRequestsOverlay.style.display = 'none';

openRequestsPopup.addEventListener('click', function() {
friendRequestsOverlay.style.display = 'flex';
});

function closeFriendRequestsPopup() {
friendRequestsOverlay.style.display = 'none';
}

friendRequestsOverlay.addEventListener('click', function(event) {
if (event.target === friendRequestsOverlay) {
    closeFriendRequestsPopup();
}
});

closeRequestsPopup.addEventListener('click', closeFriendRequestsPopup);
});


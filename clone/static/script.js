// Function to fetch the username and user ID and save them as cookies
async function fetchAndSaveUsername() {
    try {
        // Fetch the username and ID from the endpoint
        const response = await fetch('/get_username', {
            method: 'GET',
            credentials: 'include', // Include cookies with the request
        });

        // Check if the response is okay
        if (!response.ok) {
            throw new Error('Failed to fetch username and ID');
        }

        const data = await response.json();

        // Check if username and ID exist in the data
        if (data.username && data.id) {
            console.log('Fetched data:', data);

            // Save both username and user ID to cookies
            const expirationDays = 7; // Example: Keep the cookies for 7 days
            const date = new Date();
            date.setTime(date.getTime() + (expirationDays * 24 * 60 * 60 * 1000));
            const expires = `expires=${date.toUTCString()}`;

            // Save cookies with path and expiration
            document.cookie = `username=${data.username}; path=/; ${expires}`;
            document.cookie = `id=${data.id}; path=/; ${expires}`;

            console.log('Username and ID saved to cookies.');
        } else {
            console.error('Invalid data format:', data);
        }
    } catch (error) {
        console.error('Error fetching and saving username and ID:', error);
    }
}

// Function to get a cookie by name
function getCookie(name) {
    const key = name + "=";
    const decodedCookie = decodeURIComponent(document.cookie);
    const cookieArray = decodedCookie.split(';');
    for (let i = 0; i < cookieArray.length; i++) {
        let cookie = cookieArray[i].trim();
        if (cookie.indexOf(key) === 0) {
            return cookie.substring(key.length, cookie.length);
        }
    }
    return null;
}

// Function to retrieve username and ID from cookies
function getUserCookies() {
    const username = getCookie('username');
    const userId = getCookie('id');

    if (username && userId) {
        return {
            username: username,
            userId: userId,
        };
    }
    return null; // Return null if either cookie is missing
}

document.addEventListener('DOMContentLoaded', () => {
    const userCookies = getUserCookies();

    if (!userCookies || !userCookies.username || !userCookies.userId) {
        console.log('Cookies not found, fetching from server...');
        fetchAndSaveUsername();
    } else {
        console.log('User data loaded from cookies:', userCookies);
    }
});

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
                const USER = getCookie("username");
                socket.emit("send_message", { message: messageText, username: USER });
            }
        });

    // Clear input field after sending
    inputField.value = "";
}

// Redirect to the logout route
document.getElementById('lgout').addEventListener('click', function() {
        document.cookie.split(";").forEach(function(cookie) {
            const [name] = cookie.split("=");
            document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/";
    });
        window.location.href = "/logout";
});

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
    const USER = getCookie("username");

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
        const USER = getCookie("username");
        socket.emit("send_message", { message: messageText, username: USER });
    });

    inputField.value = ""; // Clear input field
    scrollToBottom();
}

async function addFriend(friendId) {
    try {
        // Ensure friendId is valid
        if (!friendId) {
            throw new Error('Friend ID is required');
        }

        // Build the URL with the friendId as a query parameter
        const url = `/add-friend?friendId=${encodeURIComponent(friendId)}`;

        // Send a GET request to the /add-friend endpoint with friendId in the URL
        const response = await fetch(url, {
            method: 'GET', // Use GET since we're sending the parameter in the URL
        });

        // Check if the response is okay
        if (response.ok) {
            const result = await response.json();
            console.log('Friend successfully added:', result);
        } else {
            throw new Error(`Failed to add friend. Status: ${response.status}`);
        }
    } catch (error) {
        console.error('Error adding friend:', error.message);
    }
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
            console.log(friendId)
            const response = await fetch(`/profile?id=${friendId}`);
            console.log(response)
            const data = await response.json();
            if (data[0]["username"]) {
                addFriend(friendId)
            } else {
                alert("User does not exist with that ID");
            }

        } catch (error) {
            alert(`User does not exist with ID ${friendId}`);
        }
    });
});


socket.on("broadcast_message", (data) => {
    const USER = getCookie("username");
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



document.addEventListener("DOMContentLoaded", function () {
    const userId = getCookie("id"); // Replace this with dynamic logic to get the user ID if necessary
    console.log(userId)

    const friendsWrapper = document.getElementById("friendsWrapper");
    const friendRequestsList = document.getElementById("friendRequestsList");

    // Fetch friends and incoming requests
    fetch(`/get-friend-data?id=${userId}`)
        .then(response => response.json())
        .then(data => {
            // Handle friends
            const friends = data.friends;
            if (friends && friends.length > 0) {
                friends.forEach(friend => {
                    // Fetch individual friend's data
                    fetch(`/profile?id=${friend}`)
                        .then(response => response.json())
                        .then(friendData => {
                            if (friendData.username) {
                                const friendElement = document.createElement("span");
                                friendElement.className = "dms";
                                friendElement.innerHTML = `
                                        <img class="pfp" src="${friendData.profile_picture}"
                                            alt="hehe">${friendData.username}
                                `;
                                friendsWrapper.appendChild(friendElement);
                            }
                        })
                        .catch(error => console.error("Error fetching friend data:", error));
                });
            } else {
                        console.log("no biches lol")

            }

            // Handle incoming requests
            const incomingRequests = data.incoming_requests;
            if (incomingRequests && incomingRequests.length > 0) {
                incomingRequests.forEach(request => {
                    const requestElement = document.createElement("div");
                    requestElement.className = "friend-request";
                    requestElement.innerHTML = `
                        <span>${request}</span>
                        <img class="accept-btn" src="/static/accept.svg" alt="Accept">
                        <img class="deny-btn" src="/static/deny.svg" alt="Deny">
                    `;
                    friendRequestsList.appendChild(requestElement);
                });
            } else {
                console.log("no incoming requests")
                friendRequestsList.innerHTML = "<div>No incoming requests</div>";
            }
        })
        .catch(error => console.error("Error fetching friends and requests:", error));
});

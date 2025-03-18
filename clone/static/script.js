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
    // Ensure socket is initialized only once
    if (!window.socket) {
        window.socket = io.connect();
        window.socket.on('connect', function () { console.log("connected") });
        window.socket.on('disconnect', function () { console.log("disconnected") });

        // Broadcast message handler
        window.socket.on("broadcast_message", async (data) => {
            const USER = getCookie("username");
            const username = data.username || "Anonymous";
            const message = data.message || "";
            const replyTo = data.replyTo;

            if (username !== USER) {
                const botMessageDiv = document.createElement("div");
                botMessageDiv.classList.add("message", "bot-message");
                botMessageDiv.dataset.messageId = Date.now();

                const messageContent = document.createElement("div");
                messageContent.classList.add("message-content");

                if (replyTo) {
                    const originalMessage = messagesContainer.querySelector(`[data-message-id="${replyTo}"] .message-content`)?.textContent || "Original message";
                    messageContent.innerHTML += `
                        <div class="replied-message" data-reply-to="${replyTo}">
                            Replying to ${username}: ${originalMessage}
                        </div>
                    `;
                }
                messageContent.innerHTML += formatMessage(message);

                const replySvg = document.createElement("img");
                replySvg.classList.add("reply-btn");
                replySvg.src = "/static/reply.svg";
                replySvg.alt = "Reply";
                replySvg.addEventListener("click", () => handleReply(botMessageDiv.dataset.messageId, username, message));

                // Fetch bot's profile picture
                let profilePicSrc = "/static/default-avatar.png";
                if (data.userId) {
                    try {
                        const response = await fetch(`/profile?id=${data.userId}`);
                        const profileData = await response.json();
                        if (profileData[0]?.image1) {
                            profilePicSrc = `data:image/jpeg;base64,${profileData[0].image1}`;
                        }
                    } catch (error) {
                        console.error("Error fetching bot profile picture:", error);
                    }
                }

                const profilePic = document.createElement("img");
                profilePic.classList.add("message-pfp");
                profilePic.src = profilePicSrc;
                profilePic.alt = "Profile Picture";

                // Structure: Profile Picture | Content | SVG
                botMessageDiv.appendChild(profilePic);
                botMessageDiv.appendChild(messageContent);
                botMessageDiv.appendChild(replySvg);

                messagesContainer.appendChild(botMessageDiv);
                scrollToBottom();
                renderLatex();
            }
        });
    }

    // Rest of your existing DOMContentLoaded code...
    const userCookies = getUserCookies();
    if (!userCookies || !userCookies.username || !userCookies.userId) {
        console.log('Cookies not found, fetching from server...');
        fetchAndSaveUsername();
    } else {
        console.log('User data loaded from cookies:', userCookies);
    }

    const inputField = document.getElementById("messageInput");
    const sendButton = document.querySelector(".send");
    const messagesContainer = document.querySelector(".messages");
    const fileInput = document.getElementById("fileInput");
    const attachmentButton = document.querySelector(".attachment");

    const replyPreview = document.getElementById("replyPreview");
    const replyToUsername = document.getElementById("replyToUsername");
    const replyMessageText = document.getElementById("replyMessageText");
    const cancelReply = document.getElementById("cancelReply");
    let replyToMessageId = null;
    let selectedFile = null;

    // Event listeners...
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
});

const inputField = document.getElementById("messageInput");
const sendButton = document.querySelector(".send");
const messagesContainer = document.querySelector(".messages");
const fileInput = document.getElementById("fileInput");
const attachmentButton = document.querySelector(".attachment");



const replyPreview = document.getElementById("replyPreview");
const replyToUsername = document.getElementById("replyToUsername");
const replyMessageText = document.getElementById("replyMessageText");
const cancelReply = document.getElementById("cancelReply");
let replyToMessageId = null; // To track the message being replied to



const socket = io.connect();
let selectedFile = null;


socket.on('connect', function () { console.log("connected") });
socket.on('disconnect', function () { console.log("disconnected") });




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
    const USER = getCookie("username");
    const username = data.username || "Anonymous";
    const message = data.message || "";
    const replyTo = data.replyTo;

    if (username !== USER) {
        const botMessageDiv = document.createElement("div");
        botMessageDiv.classList.add("message", "bot-message");
        botMessageDiv.dataset.messageId = Date.now(); // Unique ID

        // Add replied message if it exists
        if (replyTo) {
            const originalMessage = messagesContainer.querySelector(`[data-message-id="${replyTo}"] .message-content`)?.textContent || "Original message";
            botMessageDiv.innerHTML += `
                <div class="replied-message" data-reply-to="${replyTo}">
                    Replying to ${username}: ${originalMessage}
                </div>
            `;
        }

        botMessageDiv.innerHTML += formatMessage(message);

        // Add reply SVG button
        const replySvg = document.createElement("img");
        replySvg.classList.add("reply-btn");
        replySvg.src = "/static/reply.svg"; // Ensure you have a reply.svg file
        replySvg.alt = "Reply";
        replySvg.addEventListener("click", () => handleReply(botMessageDiv.dataset.messageId, username, message));
        botMessageDiv.appendChild(replySvg);

        messagesContainer.appendChild(botMessageDiv);
        scrollToBottom();
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



async function sendMessage() {
    const messageText = inputField.value.trim();
    if (messageText === "" && !selectedFile) return;

    const userMessageDiv = document.createElement("div");
    userMessageDiv.classList.add("message", "user-message");
    userMessageDiv.dataset.messageId = Date.now();

    const messageContent = document.createElement("div");
    messageContent.classList.add("message-content");

    const formData = new FormData();
    if (selectedFile) {
        formData.append("file", selectedFile);
        const fileURL = URL.createObjectURL(selectedFile);
        messageContent.innerHTML = `<a href="${fileURL}" target="_blank">${selectedFile.name}</a>`;
        selectedFile = null;
    }

    if (messageText !== "") {
        formData.append("message", messageText);
        let formattedMessage = formatMessage(messageText);

        if (replyToMessageId) {
            messageContent.innerHTML += `
                <div class="replied-message" data-reply-to="${replyToMessageId}">
                    <span class="reply-label">Replying to</span> <div class="reply-username">${getCookie("username")}</div>
                </div>
            `;
        }
        messageContent.innerHTML += formattedMessage;
    }

    // Add reply SVG
    const replySvg = document.createElement("img");
    replySvg.classList.add("reply-btn");
    replySvg.src = "/static/reply.svg";
    replySvg.alt = "Reply";
    replySvg.addEventListener("click", () => {
        const originalMessage = messageContent.textContent || messageText;
        handleReply(userMessageDiv.dataset.messageId, getCookie("username"), originalMessage);
    });

    // Fetch user's profile picture
    const userId = getCookie("id");
    let profilePicSrc = "/static/default-avatar.png"; // Fallback image
    try {
        const response = await fetch(`/profile?id=${userId}`);
        const data = await response.json();
        if (data[0]?.image1) {
            profilePicSrc = `data:image/jpeg;base64,${data[0].image1}`; // Assuming base64 encoded image
        }
    } catch (error) {
        console.error("Error fetching user profile picture:", error);
    }

    const profilePic = document.createElement("img");
    profilePic.classList.add("message-pfp");
    profilePic.src = profilePicSrc;
    profilePic.alt = "Profile Picture";

    // Structure: SVG | Content | Profile Picture (for user messages)
    userMessageDiv.appendChild(replySvg);
    userMessageDiv.appendChild(messageContent);
    userMessageDiv.appendChild(profilePic);

    messagesContainer.appendChild(userMessageDiv);
    scrollToBottom();

    formData.append("replyTo", replyToMessageId || "");
    fetch("/send_message", {
        method: "POST",
        body: formData
    }).then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const USER = getCookie("username");
                socket.emit("send_message", { message: messageText, username: USER, replyTo: replyToMessageId });
            }
        });

    inputField.value = "";
    autoResizeTextarea(inputField);
    replyToMessageId = null;
    replyPreview.style.display = "none";
}



async function sendFriendRequest(friendId) {
    try {
        // Ensure the friendId is provided
        if (!friendId) {
            alert("Friend ID is missing.");
            return;
        }

        // Make the request to the server
        const response = await fetch(`/request-friend?friendId=${friendId}`, {
            method: 'GET', // Use GET or POST depending on your server implementation
            credentials: 'include', // Include cookies with the request
        });

        // Parse the server's response
        const data = await response.json();

        // Display appropriate message based on server response
        if (response.ok) {
            // Success: Display success message
            alert(data.status || "Friend request sent successfully!");
        } else {
            // Error: Display error message
            alert(data.error || "An error occurred while sending the friend request.");
        }
    } catch (error) {
        // Handle network or unexpected errors
        console.error("Error sending friend request:", error);
        alert("An unexpected error occurred. Please try again.");
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
            const response = await fetch(`/profile?id=${friendId}`);
            const data = await response.json();
            if (data[0]["username"]) {
                sendFriendRequest(friendId);
            } else {
                alert("User does not exist with that ID");
            }

        } catch (error) {
            alert(`User does not exist with ID ${friendId}`);
        }
    });
});


socket.on("broadcast_message", async (data) => {
    const USER = getCookie("username");
    const username = data.username || "Anonymous";
    const message = data.message || "";
    const replyTo = data.replyTo;

    if (username !== USER) {
        const botMessageDiv = document.createElement("div");
        botMessageDiv.classList.add("message", "bot-message");
        botMessageDiv.dataset.messageId = Date.now();

        const messageContent = document.createElement("div");
        messageContent.classList.add("message-content");

        if (replyTo) {
            const originalMessage = messagesContainer.querySelector(`[data-message-id="${replyTo}"] .message-content`)?.textContent || "Original message";
            messageContent.innerHTML += `
                <div class="replied-message" data-reply-to="${replyTo}">
                    Replying to ${username}: ${originalMessage}
                </div>
            `;
        }
        messageContent.innerHTML += formatMessage(message);

        const replySvg = document.createElement("img");
        replySvg.classList.add("reply-btn");
        replySvg.src = "/static/reply.svg";
        replySvg.alt = "Reply";
        replySvg.addEventListener("click", () => handleReply(botMessageDiv.dataset.messageId, username, message));

        // Fetch bot's profile picture
        let profilePicSrc = "/static/default-avatar.png";
        if (data.userId) {
            try {
                const response = await fetch(`/profile?id=${data.userId}`);
                const profileData = await response.json();
                if (profileData[0]?.image1) {
                    profilePicSrc = `data:image/jpeg;base64,${profileData[0].image1}`;
                }
            } catch (error) {
                console.error("Error fetching bot profile picture:", error);
            }
        }

        const profilePic = document.createElement("img");
        profilePic.classList.add("message-pfp");
        profilePic.src = profilePicSrc;
        profilePic.alt = "Profile Picture";

        // Structure: Profile Picture | Content | SVG
        botMessageDiv.appendChild(profilePic);
        botMessageDiv.appendChild(messageContent);
        botMessageDiv.appendChild(replySvg);

        messagesContainer.appendChild(botMessageDiv);
        scrollToBottom();
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

function ensureArray(value) {
    if (!value) return [];
    return Array.isArray(value) ? value : [value];
}

document.getElementById('lgout').addEventListener('click', function() {
        document.cookie.split(";").forEach(function(cookie) {
            const [name] = cookie.split("=");
            document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/";
    });
        window.location.href = "/logout";
});

document.addEventListener("DOMContentLoaded", function () {
    const userId = getCookie("id"); // Replace this with dynamic logic to get the user ID if necessary
    console.log(userId);
    const friendsWrapper = document.getElementById("friendsWrapper");
    const friendRequestsList = document.getElementById("friendRequestsList");

    // Fetch friends and incoming requests
    fetch(`/get-friend-data?id=${userId}`)
        .then(response => response.json())
        .then(data => {
            // Handle friends
            let friends = data.friends;
            if (friends){
            friends = friends.split(",").map(Number)
            }
            friends = ensureArray(friends);
            console.log(friends);
            if (friends && friends.length > 0) {
                friends.forEach(friend => {
                    fetch(`/profile?id=${friend}`)
                        .then(response => response.json())
                        .then(friendData => {
                        friendData=friendData[0]
                            if (friendData.username) {
                                const friendElement = document.createElement("span");
                                friendElement.innerHTML = `
                                    <img class="pfp" src="data:image/jpeg;base64,${friendData.image1}" alt="hehe">
                                    ${friendData.username}
                                `;
                                friendsWrapper.appendChild(friendElement);
                            }
                        })
                        .catch(error => console.error("Error fetching friend data:", error));
                });
            } else {
                const friendElement = document.createElement("span");
                friendElement.innerHTML = `
                <img class="pfp" src="NONE" alt="hehe">
                No friends`;
                friendsWrapper.appendChild(friendElement);
            }

            // Handle incoming requests
            let incomingRequests = data.incoming_request;
            if (incomingRequests){
            incomingRequests = incomingRequests.split(",").map(Number)
            }
            incomingRequests = ensureArray(incomingRequests);

            if (incomingRequests && incomingRequests.length > 0) {
                incomingRequests.forEach(requestId => {
                    console.log("Fetching profile for request ID:", requestId);

                    if (!requestId || isNaN(requestId)) {
                        console.error("Invalid requestId:", requestId);
                        return;
                    }

                    fetch(`/profile?id=${requestId}`)
                        .then(response => {
                            if (!response.ok) {
                                throw new Error(`Failed to fetch profile for ID ${requestId}`);
                            }
                            return response.json();
                        })
                        .then(requesterData => {
                        requesterData=requesterData[0]
                            console.log("Fetched requester data:", requesterData);

                            if (!requesterData.username) {
                                throw new Error(`Username missing for ID ${requestId}`);
                            }

                            // Create friend request element
                            const requestElement = document.createElement("div");
                            requestElement.className = "friend-request";
                            requestElement.id = `request_${requestId}`; // Unique ID for removal

                            requestElement.innerHTML = `
                                <span>${requesterData.username}</span>
                                <img id="accept_${requestId}" class="accept-btn" src="/static/accept.svg" alt="Accept">
                                <img id="deny_${requestId}" class="deny-btn" src="/static/deny.svg" alt="Deny">
                            `;

                            friendRequestsList.appendChild(requestElement);

                            // Add event listeners for accept and deny buttons
                            document.getElementById(`accept_${requestId}`).addEventListener("click", function () {
                                handleFriendAction("/add_friend", requestId, requestElement);
                            });

                            document.getElementById(`deny_${requestId}`).addEventListener("click", function () {
                                handleFriendAction("/remove_request", requestId, requestElement);
                            });
                        })
                        .catch(error => console.error("Error fetching requester data:", error.message));
                });
            } else {
                console.log("no incoming requests");
                friendRequestsList.innerHTML = "<div>No incoming requests</div>";
            }
        })
        .catch(error => console.error("Error fetching friends and requests:", error));

    // Function to handle friend request actions (Accept/Deny) using GET request
    function handleFriendAction(url, requestId, requestElement) {
        fetch(`${url}?id=${requestId}`, { method: "GET" }) // Sending request ID as URL param
            .then(response => response.json())
            .then(data => {
                alert(data.status); // Alert the user with the response status

                if (data.status === "ok") {
                    requestElement.remove(); // Remove the element from the list
                }
            })
            .catch(error => console.error(`Error with ${url}:`, error));
    }
});










function handleReply(messageId, username, messageText) {
    replyToMessageId = messageId;
    replyToUsername.innerHTML = `<span class="reply-label">Replying to</span> <div class="reply-username">${username}</div>`;
    replyMessageText.textContent = messageText.length > 50 ? messageText.substring(0, 50) + "..." : messageText;
    replyPreview.style.display = "block";
    inputField.focus();
}

cancelReply.addEventListener("click", () => {
    replyToMessageId = null;
    replyPreview.style.display = "none";
    inputField.value = "";
    autoResizeTextarea(inputField);
});


messagesContainer.addEventListener("click", (e) => {
    const repliedMessage = e.target.closest(".replied-message");
    if (repliedMessage) {
        const originalMessageId = repliedMessage.dataset.replyTo;
        const originalMessage = messagesContainer.querySelector(`[data-message-id="${originalMessageId}"]`);
        if (originalMessage) {
            originalMessage.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }
});
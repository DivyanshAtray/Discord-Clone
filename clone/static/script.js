const friendId = new URLSearchParams(window.location.search).get('friend_id');

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

function handleFriendAction(url, requestId, requestElement) {
    console.log(`Calling ${url} with requestId ${requestId}`);
    fetch(`${url}?id=${requestId}`, { method: "GET" })
        .then(response => {
            console.log(`Response from ${url}:`, response);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log(`Data from ${url}:`, data);
            alert(data.status || data.error || "Action completed");

            if (data.status === "ok" || data.status === "Friend request removed successfully!") {
                console.log(`Removing request element for ID ${requestId}`);
                requestElement.remove();
            }
        })
        .catch(error => {
            console.error(`Error with ${url}:`, error);
            alert(`Error: ${error.message}`);
        });
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

const replyPreview = document.getElementById("replyPreview");
const replyToUsername = document.getElementById("replyToUsername");
const replyMessageText = document.getElementById("replyMessageText");
const cancelReply = document.getElementById("cancelReply");
let replyToMessageId = null; // To track the message being replied to

const socket = io.connect();
let selectedFile = null;

// Enhanced WebSocket debugging
socket.on("connect", () => {
    console.log("WebSocket connected successfully");
});
socket.on("disconnect", () => {
    console.log("WebSocket disconnected");
});
socket.on("connect_error", (error) => {
    console.error("WebSocket connection error:", error);
});

// Fetch initial online status of friends
function fetchOnlineStatus() {
    fetch('/get_online_status', {
        method: 'GET',
        credentials: 'include'
    })
    .then(response => response.json())
    .then(data => {
        console.log("Initial online status:", data);
        const onlineStatus = data.online_status || {};
        for (const friendId in onlineStatus) {
            const friendElement = document.querySelector(`span[data-friend-id="${friendId}"] .pfp`);
            if (friendElement) {
                if (onlineStatus[friendId] === "online") {
                    friendElement.classList.add("online");
                } else {
                    friendElement.classList.remove("online");
                }
            }
        }
    })
    .catch(error => console.error("Error fetching online status:", error));
}



// Listen for user status updates
socket.on("user_status", (data) => {
    console.log("Received user_status:", data);
    const friendId = data.user_id;
    const status = data.status;
    const friendElement = document.querySelector(`span[data-friend-id="${friendId}"] .pfp`);
    if (friendElement) {
        console.log(`Updating status for friend ${friendId}: ${status}`);
        if (status === "online") {
            friendElement.classList.add("online");
        } else {
            friendElement.classList.remove("online");
        }
    } else {
        console.log(`Friend element not found for ID ${friendId}`);
    }
});

if (cancelReply) {
    cancelReply.addEventListener("click", () => {
        console.log("Cancel reply clicked");
        replyToMessageId = null;
        replyPreview.style.display = "none";
        replyToUsername.textContent = "";
        replyMessageText.textContent = "";
        inputField.value = "";
        autoResizeTextarea(inputField);
    });
} else {
    console.warn("Cancel reply button not found");
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
    return text.replace(/</g, "<").replace(/>/g, ">");
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

async function sendMessage() {
    const messageText = inputField.value.trim();
    if (messageText === "" && !selectedFile) return;

    const USER = getCookie("username");
    const userId = getCookie("id");

    // Local rendering for your message
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", "user-message");
    const messageContent = document.createElement("div");
    messageContent.classList.add("message-content");

    if (replyToMessageId) {
        const originalMessageElement = messagesContainer.querySelector(`[data-message-id="${replyToMessageId}"] .message-content`);
        let originalMessage = originalMessageElement?.textContent || "Original message";

        // Remove the timestamp from the original message
        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = originalMessageElement?.innerHTML || originalMessage;
        const timestampDiv = tempDiv.querySelector(".message-timestamp");
        if (timestampDiv) {
            timestampDiv.remove();
        }
        originalMessage = tempDiv.textContent || tempDiv.innerText;

        // Truncate the message to 10 characters and add "...." if longer
        const truncatedMessage = originalMessage.length > 10 ? originalMessage.substring(0, 10) + "...." : originalMessage;

        messageContent.innerHTML += `
            <div class="replied-message" data-reply-to="${replyToMessageId}">
                Replying to ${USER}: ${truncatedMessage}
            </div>
        `;
    }
    if (selectedFile) {
        const fileURL = URL.createObjectURL(selectedFile);
        messageContent.innerHTML += `<a href="${fileURL}" target="_blank">${selectedFile.name}</a>`;
    }
    if (messageText !== "") {
        messageContent.innerHTML += formatMessage(messageText);
    }

    // Add timestamp (we'll set this after getting the server response)
    const timestampDiv = document.createElement("div");
    timestampDiv.classList.add("message-timestamp");
    messageContent.appendChild(timestampDiv);

    const replySvg = document.createElement("img");
    replySvg.classList.add("reply-btn");
    replySvg.src = "/static/reply.svg";
    replySvg.alt = "Reply";
    replySvg.addEventListener("click", () => handleReply(messageDiv.dataset.messageId, USER, messageText || selectedFile?.name));

    let profilePicSrc = "/static/default-avatar.png";
    try {
        const response = await fetch(`/profile?id=${userId}`);
        const profileData = await response.json();
        if (profileData[0]?.image1) {
            profilePicSrc = `data:image/jpeg;base64,${profileData[0].image1}`;
        }
    } catch (error) {
        console.error("Error fetching profile picture:", error);
    }

    const profilePic = document.createElement("img");
    profilePic.classList.add("message-pfp");
    profilePic.src = profilePicSrc;
    profilePic.alt = "Profile Picture";

    messageDiv.appendChild(replySvg);
    messageDiv.appendChild(messageContent);
    messageDiv.appendChild(profilePic);

    // Send to server
    const formData = new FormData();
    if (selectedFile) {
        formData.append("file", selectedFile);
        console.log("Sending file:", selectedFile.name);
        selectedFile = null;
    }
    if (messageText !== "") {
        formData.append("message", messageText);
        console.log("Sending message:", messageText);
    }
    formData.append("replyTo", replyToMessageId || "");
    formData.append("friend_id", friendId);

    let messageId, serverTimestamp;
    try {
        console.log("Sending POST to /send_message...");
        const response = await fetch("/send_message", {
            method: "POST",
            body: formData,
        });
        const data = await response.json();

        if (data.status === "success") {
            messageId = data.message_id;
            serverTimestamp = data.timestamp; // Use the server-assigned timestamp
            messageDiv.dataset.messageId = messageId; // Set the server-assigned ID

            // Set the timestamp for display
            if (serverTimestamp) {
                const date = new Date(serverTimestamp); // Parse as UTC
                timestampDiv.textContent = date.toLocaleTimeString(); // Convert to local timezone
            } else {
                timestampDiv.textContent = new Date().toLocaleTimeString(); // Fallback
            }

            // Insert the message in the correct position based on message ID
            const currentDate = new Date(serverTimestamp || new Date());
            const currentDateString = currentDate.toLocaleDateString();
            let inserted = false;
            let lastDate = null;
            let lastDateSeparator = null;
            const children = Array.from(messagesContainer.children);

            // Check if a date separator for the current day already exists
            let existingSeparator = null;
            for (const child of children) {
                if (child.classList.contains("date-separator") && child.textContent === "Today") {
                    existingSeparator = child;
                    break;
                }
            }

            for (let i = 0; i < children.length; i++) {
                const child = children[i];
                if (child.classList.contains("date-separator")) {
                    lastDate = child.textContent;
                    lastDateSeparator = child;
                    continue;
                }
                if (child.classList.contains("message")) {
                    const childMessageId = parseInt(child.dataset.messageId);
                    const childTimestamp = new Date(child.querySelector(".message-timestamp").textContent);
                    const childDateString = childTimestamp.toLocaleDateString();

                    // Compare message IDs
                    if (messageId < childMessageId) {
                        // If we're inserting before a message, check if we need a date separator
                        if (!existingSeparator && lastDate !== currentDateString) {
                            const dateSeparator = document.createElement("div");
                            dateSeparator.classList.add("date-separator");

                            const today = new Date();
                            const yesterday = new Date(today);
                            yesterday.setDate(today.getDate() - 1);

                            const todayString = today.toLocaleDateString();
                            const yesterdayString = yesterday.toLocaleDateString();

                            if (currentDateString === todayString) {
                                dateSeparator.textContent = "Today";
                            } else if (currentDateString === yesterdayString) {
                                dateSeparator.textContent = "Yesterday";
                            } else {
                                dateSeparator.textContent = currentDate.toLocaleDateString(undefined, {
                                    year: "numeric",
                                    month: "long",
                                    day: "numeric"
                                });
                            }

                            messagesContainer.insertBefore(dateSeparator, child);
                            i++; // Skip the newly inserted separator
                        }
                        messagesContainer.insertBefore(messageDiv, child);
                        inserted = true;
                        break;
                    }
                }
            }

            // If the message wasn't inserted (e.g., it's the newest), append it
            if (!inserted) {
                if (!existingSeparator && lastDate !== currentDateString) {
                    const dateSeparator = document.createElement("div");
                    dateSeparator.classList.add("date-separator");

                    const today = new Date();
                    const yesterday = new Date(today);
                    yesterday.setDate(today.getDate() - 1);

                    const todayString = today.toLocaleDateString();
                    const yesterdayString = yesterday.toLocaleDateString();

                    if (currentDateString === todayString) {
                        dateSeparator.textContent = "Today";
                    } else if (currentDateString === yesterdayString) {
                        dateSeparator.textContent = "Yesterday";
                    } else {
                        dateSeparator.textContent = currentDate.toLocaleDateString(undefined, {
                            year: "numeric",
                            month: "long",
                            day: "numeric"
                        });
                    }

                    messagesContainer.appendChild(dateSeparator);
                }
                messagesContainer.appendChild(messageDiv);
            }

            scrollToBottom();
            renderLatex();

            console.log("POST successful, emitting socket message:", {
                message: messageText,
                username: USER,
                userId: userId,
                friendId: friendId,
                replyTo: replyToMessageId,
                timestamp: serverTimestamp || new Date().toISOString(),
                file_location: selectedFile ? selectedFile.name : null,
                message_id: messageId
            });
            socket.emit("send_message", {
                message: messageText,
                username: USER,
                userId: userId,
                friendId: friendId,
                replyTo: replyToMessageId,
                timestamp: serverTimestamp || new Date().toISOString(),
                file_location: selectedFile ? selectedFile.name : null,
                message_id: messageId
            });
        } else {
            console.error("Server rejected message:", data);
        }
    } catch (error) {
        console.error("Error during sendMessage:", error);
    }

    inputField.value = "";
    autoResizeTextarea(inputField);
    replyToMessageId = null;
    replyPreview.style.display = "none";
}

socket.on("broadcast_message", async (data) => {
    console.log("Received broadcast_message:", data);

    const USER = getCookie("username");
    const userId = getCookie("id");
    const username = data.username || "Anonymous";
    const message = data.message || "";
    const senderId = data.userId;
    const recipientId = data.friendId;
    const replyTo = data.replyTo;
    const timestamp = data.timestamp || new Date().toISOString();
    const file_location = data.file_location;
    const messageId = data.message_id;
    let seen = data.seen || 0; // Get the seen status

    // Skip if no valid data
    if (!username || (!message && !file_location) || !messageId) {
        console.error("Invalid broadcast data:", data);
        return;
    }

    // Filter messages: Display only if part of the current conversation
    const isFromCurrentUserToFriend = (senderId == userId && recipientId == friendId);
    const isFromFriendToCurrentUser = (senderId == friendId && recipientId == userId);
    if (!(isFromCurrentUserToFriend || isFromFriendToCurrentUser)) {
        console.log("Message not for this conversation, skipping...");
        // Fetch updated unread counts
        fetchUnreadCounts();
        return;
    }

    // Skip your own message (already rendered locally in sendMessage)
    if (username === USER && isFromCurrentUserToFriend) {
        console.log("Skipping own message (rendered locally)");
        return;
    }

    console.log("Rendering friend’s message from:", username);

    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", "bot-message");

    // Check if the message is visible immediately (e.g., chat is at the bottom)
    const isAtBottom = messagesContainer.scrollHeight - messagesContainer.scrollTop <= messagesContainer.clientHeight + 50; // Within 50px of the bottom
    if (isAtBottom && !seen) {
        // Mark the message as seen immediately since the user is viewing the chat
        try {
            const response = await fetch("/mark_messages_seen", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    message_ids: [messageId],
                    friend_id: friendId
                }),
                credentials: "include"
            });

            if (!response.ok) {
                console.error(`Failed to mark new message ${messageId} as seen: HTTP ${response.status}`);
                const text = await response.text();
                console.error("Response body:", text);
                return;
            }

            const data = await response.json();
            if (data.status === "success") {
                seen = 1; // Update the seen status
                console.log(`Marked new message ${messageId} as seen immediately`);
                // Fetch updated unread counts
                fetchUnreadCounts();
            }
        } catch (error) {
            console.error("Error marking new message as seen:", error);
        }
    }

    messageDiv.dataset.messageId = messageId;
    messageDiv.dataset.seen = seen ? "1" : "0"; // Add seen status
    if (!seen) {
        // Fetch updated unread counts after marking as seen
        fetchUnreadCounts();
    }
    const messageContent = document.createElement("div");
    messageContent.classList.add("message-content");

    if (replyTo) {
        const originalMessageElement = messagesContainer.querySelector(`[data-message-id="${replyTo}"] .message-content`);
        let originalMessage = originalMessageElement?.textContent || "Original message";

        // Remove the timestamp from the original message
        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = originalMessageElement?.innerHTML || originalMessage;
        const timestampDiv = tempDiv.querySelector(".message-timestamp");
        if (timestampDiv) {
            timestampDiv.remove();
        }
        originalMessage = tempDiv.textContent || tempDiv.innerText;

        // Truncate the message to 10 characters and add "...." if longer
        const truncatedMessage = originalMessage.length > 10 ? originalMessage.substring(0, 10) + "...." : originalMessage;

        messageContent.innerHTML += `
            <div class="replied-message" data-reply-to="${replyTo}">
                Replying to ${username}: ${truncatedMessage}
            </div>
        `;
    }
    if (file_location) {
        messageContent.innerHTML += `<a href="/uploads/${file_location}" target="_blank">${file_location}</a>`;
    }
    if (message) {
        messageContent.innerHTML += formatMessage(message);
    }

    const timestampDiv = document.createElement("div");
    timestampDiv.classList.add("message-timestamp");
    timestampDiv.textContent = new Date(timestamp).toLocaleTimeString(); // Parse as UTC and convert to local
    messageContent.appendChild(timestampDiv);

    const replySvg = document.createElement("img");
    replySvg.classList.add("reply-btn");
    replySvg.src = "/static/reply.svg";
    replySvg.alt = "Reply";
    replySvg.addEventListener("click", () => handleReply(messageDiv.dataset.messageId, username, message || file_location));

    let profilePicSrc = "/static/default-avatar.png";
    if (senderId) {
        try {
            const response = await fetch(`/profile?id=${senderId}`);
            const profileData = await response.json();
            if (profileData[0]?.image1) {
                profilePicSrc = `data:image/jpeg;base64,${profileData[0].image1}`;
            }
        } catch (error) {
            console.error("Error fetching profile picture:", error);
        }
    }

    const profilePic = document.createElement("img");
    profilePic.classList.add("message-pfp");
    profilePic.src = profilePicSrc;
    profilePic.alt = "Profile Picture";

    messageDiv.appendChild(profilePic);
    messageDiv.appendChild(messageContent);
    messageDiv.appendChild(replySvg);

    // Insert the message in the correct position based on message ID
    const currentDate = new Date(timestamp);
    const currentDateString = currentDate.toLocaleDateString();
    let inserted = false;
    let lastDate = null;
    let lastDateSeparator = null;
    const children = Array.from(messagesContainer.children);

    // Check if a date separator for the current day already exists
    let existingSeparator = null;
    for (const child of children) {
        if (child.classList.contains("date-separator") && child.textContent === "Today") {
            existingSeparator = child;
            break;
        }
    }

    for (let i = 0; i < children.length; i++) {
        const child = children[i];
        if (child.classList.contains("date-separator")) {
            lastDate = child.textContent;
            lastDateSeparator = child;
            continue;
        }
        if (child.classList.contains("message")) {
            const childMessageId = parseInt(child.dataset.messageId);
            const childTimestamp = new Date(child.querySelector(".message-timestamp").textContent);
            const childDateString = childTimestamp.toLocaleDateString();

            // Compare message IDs
            if (messageId < childMessageId) {
                // If we're inserting before a message, check if we need a date separator
                if (!existingSeparator && lastDate !== currentDateString) {
                    const dateSeparator = document.createElement("div");
                    dateSeparator.classList.add("date-separator");

                    const today = new Date();
                    const yesterday = new Date(today);
                    yesterday.setDate(today.getDate() - 1);

                    const todayString = today.toLocaleDateString();
                    const yesterdayString = yesterday.toLocaleDateString();

                    if (currentDateString === todayString) {
                        dateSeparator.textContent = "Today";
                    } else if (currentDateString === yesterdayString) {
                        dateSeparator.textContent = "Yesterday";
                    } else {
                        dateSeparator.textContent = currentDate.toLocaleDateString(undefined, {
                            year: "numeric",
                            month: "long",
                            day: "numeric"
                        });
                    }

                    messagesContainer.insertBefore(dateSeparator, child);
                    i++; // Skip the newly inserted separator
                }
                messagesContainer.insertBefore(messageDiv, child);
                inserted = true;
                break;
            }
        }
    }

    // If the message wasn't inserted (e.g., it's the newest), append it
    if (!inserted) {
        if (!existingSeparator && lastDate !== currentDateString) {
            const dateSeparator = document.createElement("div");
            dateSeparator.classList.add("date-separator");

            const today = new Date();
            const yesterday = new Date(today);
            yesterday.setDate(today.getDate() - 1);

            const todayString = today.toLocaleDateString();
            const yesterdayString = yesterday.toLocaleDateString();

            if (currentDateString === todayString) {
                dateSeparator.textContent = "Today";
            } else if (currentDateString === yesterdayString) {
                dateSeparator.textContent = "Yesterday";
            } else {
                dateSeparator.textContent = currentDate.toLocaleDateString(undefined, {
                    year: "numeric",
                    month: "long",
                    day: "numeric"
                });
            }

            messagesContainer.appendChild(dateSeparator);
        }
        messagesContainer.appendChild(messageDiv);
    }

    scrollToBottom();
    renderLatex();
    observeUnreadMessages(); // Observe the new message for visibility
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

// Set up Intersection Observer to mark messages as seen when they become visible
const observerOptions = {
    root: messagesContainer, // Use the messages container as the root
    rootMargin: "0px",
    threshold: 0.1 // Trigger when 10% of the message is visible
};

const observer = new IntersectionObserver((entries, observer) => {
    entries.forEach(async (entry) => {
        if (entry.isIntersecting) {
            console.log("Message is visible in viewport:", entry.target.dataset.messageId);

            const messageDiv = entry.target;
            const messageId = messageDiv.dataset.messageId;
            const userId = getCookie("id");
            const friendId = new URLSearchParams(window.location.search).get('friend_id');
            const senderId = messageDiv.classList.contains("bot-message") ? friendId : userId;

            // Only mark messages from friends as seen
            if (!messageDiv.classList.contains("bot-message")) {
                console.log("Skipping message - not a bot-message:", messageId);
                return;
            }

            // Wait 3 seconds before marking as seen
            setTimeout(async () => {
                console.log(`Marking message ${messageId} as seen for friend ${friendId}`);

                // Mark the message as seen on the server
                try {
                    const response = await fetch("/mark_messages_seen", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            message_ids: [messageId],
                            friend_id: friendId
                        }),
                        credentials: "include"
                    });

                    if (!response.ok) {
                        console.error(`Failed to mark message ${messageId} as seen: HTTP ${response.status}`);
                        const text = await response.text();
                        console.error("Response body:", text);
                        return;
                    }

                    const data = await response.json();
                    if (data.status === "success") {
                        console.log(`Successfully marked message ${messageId} as seen after 3 seconds`);
                        messageDiv.dataset.seen = "1"; // Update the seen status in the DOM
                        // Check if there are any remaining unread messages from this friend
                        const remainingUnread = messagesContainer.querySelectorAll(`.message.bot-message[data-sender-id="${senderId}"]:not([data-seen="1"])`);
                        if (remainingUnread.length === 0) {
                            console.log(`No more unread messages from friend ${senderId}, updating unread counts`);
                            fetchUnreadCounts();
                        }
                    } else {
                        console.error("Failed to mark message as seen:", data);
                    }
                } catch (error) {
                    console.error("Error marking message as seen:", error);
                }
            }, 3000); // 3-second delay

            // Stop observing this message
            observer.unobserve(messageDiv);
        }
    });
}, observerOptions);

// Function to observe unread messages
function observeUnreadMessages() {
    const unreadMessages = messagesContainer.querySelectorAll(".message.bot-message:not([data-seen='1'])");
    console.log(`Observing ${unreadMessages.length} unread messages`);
    unreadMessages.forEach((message) => {
        message.dataset.senderId = new URLSearchParams(window.location.search).get('friend_id');
        observer.observe(message);
    });
}

async function fetchUnreadCounts() {
    try {
        const response = await fetch('/get_unread_counts', {
            method: 'GET',
            credentials: 'include'
        });

        if (!response.ok) {
            console.error(`Failed to fetch unread counts: HTTP ${response.status}`);
            return;
        }

        const data = await response.json();
        const unreadCounts = data.unread_counts || {};
        console.log("Unread counts:", unreadCounts);

        // Update the sidebar based on unread counts
        for (const friendId in unreadCounts) {
            const count = unreadCounts[friendId];
            const friendItem = document.querySelector(`span[data-friend-id="${friendId}"]`);
            if (friendItem) {
                if (count > 0) {
                    console.log(`Adding 'unread' class to friend ${friendId} (count: ${count})`);
                    friendItem.classList.add("unread");
                } else {
                    console.log(`Removing 'unread' class from friend ${friendId} (count: ${count})`);
                    friendItem.classList.remove("unread");
                }
            }
        }
    } catch (error) {
        console.error("Error fetching unread counts:", error);
    }
}

document.getElementById('lgout').addEventListener('click', function() {
    document.cookie.split(";").forEach(function(cookie) {
        const [name] = cookie.split("=");
        document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/";
    });
    window.location.href = "/logout";
});

document.addEventListener("DOMContentLoaded", async function () {
    let userId = getCookie("id");
    if (!userId) {
        console.log("User ID not found in cookies, fetching from server...");
        await fetchAndSaveUsername();
        userId = getCookie("id");
    }

    const friendsWrapper = document.getElementById("friendsWrapper");
    const friendRequestsList = document.getElementById("friendRequestsList");

    let messageOffset = 0;
    const messageLimit = 50;
    let isLoadingMessages = false;
    let allMessagesLoaded = false;

    async function loadMessages(offset = 0, append = false) {
        if (isLoadingMessages || allMessagesLoaded) return;
        isLoadingMessages = true;

        try {
            const response = await fetch(`/messages?friend_id=${friendId}&limit=${messageLimit}&offset=${offset}`);
            const messages = await response.json();

            if (messages.length < messageLimit) {
                allMessagesLoaded = true;
            }

            let lastDate = null;
            const existingSeparators = new Set();

            if (append) {
                const children = Array.from(messagesContainer.children);
                for (const child of children) {
                    if (child.classList.contains("date-separator")) {
                        existingSeparators.add(child.textContent);
                    }
                }
            }

            for (const msg of messages) {
                const messageDate = new Date(msg.timestamp);
                const messageDateString = messageDate.toLocaleDateString();

                const today = new Date();
                const yesterday = new Date(today);
                yesterday.setDate(today.getDate() - 1);

                const todayString = today.toLocaleDateString();
                const yesterdayString = yesterday.toLocaleDateString();

                let dateLabel;
                if (messageDateString === todayString) {
                    dateLabel = "Today";
                } else if (messageDateString === yesterdayString) {
                    dateLabel = "Yesterday";
                } else {
                    dateLabel = messageDate.toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "long",
                        day: "numeric"
                    });
                }

                if (lastDate !== messageDateString && !existingSeparators.has(dateLabel)) {
                    const dateSeparator = document.createElement("div");
                    dateSeparator.classList.add("date-separator");
                    dateSeparator.textContent = dateLabel;

                    if (append) {
                        messagesContainer.insertBefore(dateSeparator, messagesContainer.firstChild);
                    } else {
                        messagesContainer.appendChild(dateSeparator);
                    }

                    existingSeparators.add(dateLabel);
                    lastDate = messageDateString;
                }

                const messageDiv = document.createElement("div");
                const isUserMessage = msg.username === getCookie("username");
                messageDiv.classList.add("message", isUserMessage ? "user-message" : "bot-message");
                messageDiv.dataset.messageId = msg.id;
                messageDiv.dataset.seen = msg.seen ? "1" : "0";
                if (!isUserMessage && !msg.seen) {
                    fetchUnreadCounts();
                }
                const messageContent = document.createElement("div");
                messageContent.classList.add("message-content");

                if (msg.reply_to) {
                    const originalMessageElement = messagesContainer.querySelector(`[data-message-id="${msg.reply_to}"] .message-content`);
                    let originalMessage = originalMessageElement?.textContent || msg.message || "Original message";

                    const tempDiv = document.createElement("div");
                    tempDiv.innerHTML = originalMessageElement?.innerHTML || originalMessage;
                    const timestampDiv = tempDiv.querySelector(".message-timestamp");
                    if (timestampDiv) {
                        timestampDiv.remove();
                    }
                    originalMessage = tempDiv.textContent || tempDiv.innerText;

                    const truncatedMessage = originalMessage.length > 10 ? originalMessage.substring(0, 10) + "...." : originalMessage;

                    messageContent.innerHTML += `
                        <div class="replied-message" data-reply-to="${msg.reply_to}">
                            Replying to ${msg.username}: ${truncatedMessage}
                        </div>
                    `;
                }

                if (msg.file_location) {
                    messageContent.innerHTML += `<a href="/uploads/${msg.file_location}" target="_blank">${msg.file_location}</a>`;
                }
                if (msg.message) {
                    messageContent.innerHTML += formatMessage(msg.message);
                }

                const timestampDiv = document.createElement("div");
                timestampDiv.classList.add("message-timestamp");
                timestampDiv.textContent = new Date(msg.timestamp).toLocaleTimeString();
                messageContent.appendChild(timestampDiv);

                const replySvg = document.createElement("img");
                replySvg.classList.add("reply-btn");
                replySvg.src = "/static/reply.svg";
                replySvg.alt = "Reply";

                let replyMessage = msg.message || msg.file_location || "";
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = replyMessage;
                const timestampDiv2 = tempDiv.querySelector(".message-timestamp");
                if (timestampDiv2) {
                    timestampDiv2.remove();
                }
                replyMessage = tempDiv.textContent || tempDiv.innerText;

                replySvg.addEventListener("click", () => handleReply(messageDiv.dataset.messageId, msg.username, replyMessage));

                let profilePicSrc = "/static/default-avatar.png";
                const profileId = msg.username === getCookie("username") ? userId : friendId;
                try {
                    const response = await fetch(`/profile?id=${profileId}`);
                    const profileData = await response.json();
                    if (profileData[0]?.image1) {
                        profilePicSrc = `data:image/jpeg;base64,${profileData[0].image1}`;
                    }
                } catch (error) {
                    console.error("Error fetching profile picture:", error);
                }

                const profilePic = document.createElement("img");
                profilePic.classList.add("message-pfp");
                profilePic.src = profilePicSrc;
                profilePic.alt = "Profile Picture";

                messageDiv.appendChild(isUserMessage ? replySvg : profilePic);
                messageDiv.appendChild(messageContent);
                messageDiv.appendChild(isUserMessage ? profilePic : replySvg);

                if (append) {
                    messagesContainer.insertBefore(messageDiv, messagesContainer.firstChild);
                } else {
                    messagesContainer.appendChild(messageDiv);
                }
            }

            if (!append) {
                scrollToBottom();
            }
            renderLatex();
            messageOffset += messages.length;
            observeUnreadMessages();

            if (friendId) {
                setTimeout(async () => {
                    const unreadMessages = messagesContainer.querySelectorAll(`.message.bot-message:not([data-seen="1"])`);
                    const messageIds = Array.from(unreadMessages).map(msg => msg.dataset.messageId);
                    if (messageIds.length > 0) {
                        try {
                            const response = await fetch("/mark_messages_seen", {
                                method: "POST",
                                headers: {
                                    "Content-Type": "application/json"
                                },
                                body: JSON.stringify({
                                    message_ids: messageIds,
                                    friend_id: friendId
                                }),
                                credentials: "include"
                            });

                            if (!response.ok) {
                                console.error(`Failed to mark messages as seen: HTTP ${response.status}`);
                                const text = await response.text();
                                console.error("Response body:", text);
                                return;
                            }

                            const data = await response.json();
                            if (data.status === "success") {
                                console.log(`Successfully marked messages ${messageIds} as seen after 3 seconds`);
                                unreadMessages.forEach(msg => msg.dataset.seen = "1");
                                fetchUnreadCounts();
                            }
                        } catch (error) {
                            console.error("Error marking messages as seen after 3 seconds:", error);
                        }
                    }
                }, 3000);
            }
        } catch (error) {
            console.error("Error fetching messages:", error);
        } finally {
            isLoadingMessages = false;
        }
    }

    if (friendId) {
        await loadMessages();
    }

    messagesContainer.addEventListener("scroll", () => {
        if (messagesContainer.scrollTop === 0 && !isLoadingMessages && !allMessagesLoaded) {
            loadMessages(messageOffset, true);
        }
    });

    if (!userId) {
        console.error("No user ID available, cannot fetch friend data");
        if (friendRequestsList) {
            friendRequestsList.innerHTML = "<div>Error: User not logged in</div>";
        }
        return;
    }

    fetch(`/get-friend-data?id=${userId}`)
        .then(response => {
            console.log("Response from /get-friend-data:", response);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Data from /get-friend-data:", data);

            let friends = data.friends;
            if (friends) {
                friends = friends.split(",").map(Number);
            }
            friends = ensureArray(friends);
            console.log("Parsed friends:", friends);
            if (friends && friends.length > 0) {
                friends.forEach(friend => {
                    fetch(`/profile?id=${friend}`)
                        .then(response => response.json())
                        .then(friendData => {
                            friendData = friendData[0];
                            if (friendData.username) {
                                const friendElement = document.createElement("span");
                                friendElement.setAttribute("data-friend-id", friend);
                                friendElement.innerHTML = `
                                    <img class="pfp" src="data:image/jpeg;base64,${friendData.image1}" alt="hehe">
                                    ${friendData.username}
                                `;

                                friendElement.addEventListener("click", async () => {
                                    try {
                                        const response = await fetch("/mark_messages_seen", {
                                            method: "POST",
                                            headers: {
                                                "Content-Type": "application/json"
                                            },
                                            body: JSON.stringify({
                                                message_ids: [],
                                                friend_id: friend
                                            }),
                                            credentials: "include"
                                        });

                                        if (response.ok) {
                                            console.log(`Marked messages as seen for friend ${friend}`);
                                            fetchUnreadCounts();
                                        }
                                    } catch (error) {
                                        console.error("Error marking messages as seen:", error);
                                    }
                                    window.location.href = `/?friend_id=${friend}`;
                                });

                                friendsWrapper.appendChild(friendElement);
                            }
                        })
                        .catch(error => console.error("Error fetching friend data:", error));
                });

                // Periodically fetch online status as a fallback
                setInterval(() => {
                    console.log("Polling online status...");
                    fetchOnlineStatus();
                }, 10000);
            } else {
                const friendElement = document.createElement("span");
                friendElement.innerHTML = `
                    <img class="pfp" src="NONE" alt="hehe">
                    No friends`;
                friendsWrapper.appendChild(friendElement);
            }

            let incomingRequests = data.incoming_request;
            console.log("Raw incoming_requests:", incomingRequests);
            if (incomingRequests) {
                incomingRequests = incomingRequests.split(",").map(Number);
            }
            incomingRequests = ensureArray(incomingRequests);
            console.log("Parsed incomingRequests:", incomingRequests);

            if (incomingRequests && incomingRequests.length > 0) {
                incomingRequests.forEach(requestId => {
                    console.log("Fetching profile for request ID:", requestId);

                    if (!requestId || isNaN(requestId)) {
                        console.error("Invalid requestId:", requestId);
                        return;
                    }

                    fetch(`/profile?id=${requestId}`)
                        .then(response => {
                            console.log(`Response from /profile?id=${requestId}:`, response);
                            if (!response.ok) {
                                throw new Error(`Failed to fetch profile for ID ${requestId}`);
                            }
                            return response.json();
                        })
                        .then(requesterData => {
                            requesterData = requesterData[0];
                            console.log("Fetched requester data:", requesterData);

                            if (!requesterData.username) {
                                throw new Error(`Username missing for ID ${requestId}`);
                            }

                            const requestElement = document.createElement("div");
                            requestElement.className = "friend-request";
                            requestElement.id = `request_${requestId}`;

                            requestElement.innerHTML = `
                                <span>${requesterData.username}</span>
                                <img id="accept_${requestId}" class="accept-btn" src="/static/accept.svg" alt="Accept">
                                <img id="deny_${requestId}" class="deny-btn" src="/static/deny.svg" alt="Deny">
                            `;

                            friendRequestsList.appendChild(requestElement);
                            console.log("Appended request element for ID:", requestId);

                            const acceptButton = document.getElementById(`accept_${requestId}`);
                            const denyButton = document.getElementById(`deny_${requestId}`);
                            console.log(`Accept button for ID ${requestId}:`, acceptButton);
                            console.log(`Deny button for ID ${requestId}:`, denyButton);

                            if (acceptButton) {
                                acceptButton.addEventListener("click", function () {
                                    console.log(`Accept button clicked for request ID ${requestId}`);
                                    handleFriendAction("/add_friend", requestId, requestElement);
                                });
                            } else {
                                console.error(`Accept button not found for request ID ${requestId}`);
                            }

                            if (denyButton) {
                                denyButton.addEventListener("click", function () {
                                    console.log(`Deny button clicked for request ID ${requestId}`);
                                    handleFriendAction("/remove_request", requestId, requestElement);
                                });
                            } else {
                                console.error(`Deny button not found for request ID ${requestId}`);
                            }
                        })
                        .catch(error => console.error("Error fetching requester data:", error.message));
                });
            } else {
                console.log("No incoming requests");
                friendRequestsList.innerHTML = "<div>No incoming requests</div>";
            }
        })
        .catch(error => {
            console.error("Error fetching friends and requests:", error);
            if (friendRequestsList) {
                friendRequestsList.innerHTML = "<div>Error fetching friend requests</div>";
            }
        });
});

function handleReply(messageId, username, message) {
    replyToMessageId = messageId;
    replyPreview.style.display = "flex"; // Use flex to match CSS

    // Truncate the message to 10 characters and add "...." if longer
    let truncatedMessage = message.length > 10 ? message.substring(0, 10) + "...." : message;

    // Remove any timestamp from the message (in case it's included)
    const tempDiv = document.createElement("div");
    tempDiv.innerHTML = truncatedMessage;
    const timestampDiv = tempDiv.querySelector(".message-timestamp");
    if (timestampDiv) {
        timestampDiv.remove();
    }
    truncatedMessage = tempDiv.textContent || tempDiv.innerText;

    // Update the username and message text
    replyToUsername.textContent = username;
    replyMessageText.textContent = truncatedMessage;
    replyPreview.dataset.messageId = messageId;

    inputField.focus(); // Focus the input field for user convenience
}



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










document.addEventListener('DOMContentLoaded', () => {
    console.log('Chatroom script loaded');

    // Elements
    const sidebar = document.querySelector('.sidebar');
    const rightbar = document.querySelector('.rightbar');
    const sidebarOverlay = document.querySelector('.sidebar-overlay');
    const hamburgerIcon = document.querySelector('.hamburger-icon');
    const userInfo = document.querySelector('.user-info');

    console.log('Elements:', { sidebar, rightbar, sidebarOverlay, hamburgerIcon, userInfo });

    // Touch gesture variables
    let touchStartX = 0;
    let touchEndX = 0;
    const swipeThreshold = 30;
    const edgeThreshold = 100;

    // Toggle sidebar (for hamburger icon click)
    function toggleSidebar() {
        console.log('Toggling sidebar');
        sidebar.classList.toggle('open');
        updateOverlay();
    }

    // Toggle rightbar (for user info click)
    function toggleRightbar() {
        console.log('Toggling rightbar');
        rightbar.classList.toggle('open');
        updateOverlay();
    }

    // Update overlay visibility
    function updateOverlay() {
        const isSidebarOpen = sidebar.classList.contains('open');
        const isRightbarOpen = rightbar.classList.contains('open');
        console.log(`Updating overlay: Sidebar open=${isSidebarOpen}, Rightbar open=${isRightbarOpen}`);
        sidebarOverlay.classList.toggle('active', isSidebarOpen || isRightbarOpen);
    }

    // Close both sidebar and rightbar (for overlay click)
    function closeBars() {
        console.log('Closing both bars');
        sidebar.classList.remove('open');
        rightbar.classList.remove('open');
        sidebarOverlay.classList.remove('active');
    }

    // Handle touch start
    function handleTouchStart(event) {
        touchStartX = event.touches[0].clientX;
        console.log(`Touch start: X=${touchStartX}, Window width=${window.innerWidth}`);
    }

    // Handle touch move
    function handleTouchMove(event) {
        touchEndX = event.touches[0].clientX;
        console.log(`Touch move: X=${touchEndX}`);
    }

    // Handle touch end (detect swipe)
    function handleTouchEnd(event) {
        touchEndX = event.changedTouches[0].clientX;
        const swipeDistance = touchEndX - touchStartX;
        console.log(`Touch end: StartX=${touchStartX}, EndX=${touchEndX}, SwipeDistance=${swipeDistance}`);

        // Check if the screen width is less than 1320px
        if (window.innerWidth <= 820) {
            const isSidebarOpen = sidebar.classList.contains('open');
            const isRightbarOpen = rightbar.classList.contains('open');
            console.log(`Screen width <= 820px: Sidebar open=${isSidebarOpen}, Rightbar open=${isRightbarOpen}`);
            console.log(`Edge conditions: Left edge=${touchStartX <= edgeThreshold}, Right edge=${touchStartX >= window.innerWidth - edgeThreshold}`);

            // Detect swipe to open sidebar (swipe right from left edge)
            if (touchStartX <= edgeThreshold && swipeDistance > swipeThreshold) {
                console.log('Swiped right from left edge - opening sidebar');
                sidebar.classList.add('open');
                updateOverlay();
            }
            // Detect swipe to open rightbar (swipe left from right edge)
            else if (touchStartX >= window.innerWidth - edgeThreshold && swipeDistance < -swipeThreshold) {
                console.log('Swiped left from right edge - opening rightbar');
                rightbar.classList.add('open');
                updateOverlay();
            }
            // Detect swipe to close sidebar (swipe left on sidebar)
            else if (isSidebarOpen && swipeDistance < -swipeThreshold) {
                console.log('Swiped left on sidebar - closing sidebar');
                sidebar.classList.remove('open');
                updateOverlay();
            }
            // Detect swipe to close rightbar (swipe right on rightbar)
            else if (isRightbarOpen && swipeDistance > swipeThreshold) {
                console.log('Swiped right on rightbar - closing rightbar');
                rightbar.classList.remove('open');
                updateOverlay();
            }
            else {
                console.log('No swipe action triggered');
            }
        } else {
            console.log('Screen width > 820px - gestures disabled');
        }
    }

    // Event listeners for clicks (with null checks)
    if (hamburgerIcon) {
        hamburgerIcon.addEventListener('click', toggleSidebar);
    } else {
        console.warn('Hamburger icon not found');
    }

    if (userInfo) {
        userInfo.addEventListener('click', toggleRightbar);
    } else {
        console.warn('User info not found');
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeBars);
    } else {
        console.warn('Sidebar overlay not found');
    }

    // Event listeners for touch gestures (use capture phase)
    document.addEventListener('touchstart', handleTouchStart, true);
    document.addEventListener('touchmove', handleTouchMove, true);
    document.addEventListener('touchend', handleTouchEnd, true);

    // Prevent default touch behavior on sidebar and rightbar to allow swiping
    if (sidebar) {
        sidebar.addEventListener('touchstart', (e) => e.stopPropagation());
    }

    if (rightbar) {
        rightbar.addEventListener('touchstart', (e) => e.stopPropagation());
    }
});
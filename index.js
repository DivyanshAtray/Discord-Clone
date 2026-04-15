socket.on("broadcast_message", async (data) => {
    console.log("broadcast_message: Received broadcast_message:", data);

    const USER = getCookie("username");
    const isUserMessage = data.username === USER;
    if (!isUserMessage) {
        if (!isTabFocused()) {
            console.log("broadcast_message: Tab is not in focus, playing notification sound");
            try {
                await notificationSound.play();
                console.log("broadcast_message: Notification sound played successfully");
            } catch (error) {
                console.error("broadcast_message: Error playing notification sound:", error);
            }
        } else {
            console.log("broadcast_message: Tab is in focus, no notification sound needed");
        }
    } else {
        console.log("broadcast_message: Message is from the user, no notification needed");
        return;
    }

    const userId = getCookie("id");
    const username = data.username || "Anonymous";
    const message = data.message || "";
    const senderId = data.userId;
    const recipientId = data.friendId;
    const replyTo = data.replyTo;
    const timestamp = data.timestamp || new Date().toISOString();
    const fileLocation = data.file_location;
    const messageId = data.message_id;
    let seen = data.seen || 0;

    if (!username || (!message && !fileLocation) || !messageId) {
        console.error("broadcast_message: Invalid broadcast data:", data);
        return;
    }

    const isFromCurrentUserToFriend = (senderId == userId && recipientId == friendId);
    const isFromFriendToCurrentUser = (senderId == friendId && recipientId == userId);
    if (!(isFromCurrentUserToFriend || isFromFriendToCurrentUser)) {
        console.log("broadcast_message: Message not for this conversation, skipping...");
        fetchUnreadCounts();
        return;
    }

    console.log("broadcast_message: Rendering friend’s message from:", username);

    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", "bot-message");

    const isAtBottom = messagesContainer.scrollHeight - messagesContainer.scrollTop <= messagesContainer.clientHeight + 50;
    if (isAtBottom && !seen) {
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
                console.error(`broadcast_message: Failed to mark new message ${messageId} as seen: HTTP ${response.status}`);
                const text = await response.text();
                console.error("broadcast_message: Response body:", text);
                return;
            }

            const data = await response.json();
            if (data.status === "success") {
                seen = 1;
                console.log(`broadcast_message: Marked new message ${messageId} as seen immediately`);
                fetchUnreadCounts();
            }
        } catch (error) {
            console.error("broadcast_message: Error marking new message as seen:", error);
        }
    }

    messageDiv.dataset.messageId = messageId;
    messageDiv.dataset.seen = seen ? "1" : "0";
    if (!seen) {
        fetchUnreadCounts();
    }
    const messageContent = document.createElement("div");
    messageContent.classList.add("message-content");

    if (replyTo) {
        const originalMessageElement = messagesContainer.querySelector(`[data-message-id="${replyTo}"] .message-content`);
        let originalMessage = originalMessageElement?.textContent || "Original message";

        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = originalMessageElement?.innerHTML || originalMessage;
        const timestampDiv = tempDiv.querySelector(".message-timestamp");
        if (timestampDiv) {
            timestampDiv.remove();
        }
        originalMessage = tempDiv.textContent || tempDiv.innerText;

        const truncatedMessage = originalMessage.length > 10 ? originalMessage.substring(0, 10) + "...." : originalMessage;

        const replyDiv = document.createElement("div");
        replyDiv.classList.add("replied-message");
        replyDiv.dataset.replyTo = replyTo;
        replyDiv.textContent = `Replying to ${username}: ${truncatedMessage}`;
        messageContent.appendChild(replyDiv);
    }

    // Render the attachment as a child element
    if (fileLocation) {
        console.log("broadcast_message: Rendering Real-time Aesthetic Embed...");
        
        // This calls the upgraded function we created in the previous step
        const embedElement = renderAttachment(fileLocation);
        
        if (embedElement) {
            // Force the message container to be block so embeds stack nicely
            messageContent.style.display = "block"; 
            messageContent.appendChild(embedElement);
            
            // FIX: Use your existing scrollToBottom function instead of looking for a missing ID
            setTimeout(scrollToBottom, 100);
        }
    }

    // Render the message text
    if (message) {
        const messageTextDiv = document.createElement("div");
        messageTextDiv.innerHTML = formatMessage(message);
        messageContent.appendChild(messageTextDiv);
    }

    const timestampDiv = document.createElement("div");
    timestampDiv.classList.add("message-timestamp");
    timestampDiv.textContent = new Date(timestamp).toLocaleTimeString();
    messageContent.appendChild(timestampDiv);

    const replySvg = document.createElement("img");
    replySvg.classList.add("reply-btn");
    replySvg.src = "/static/reply.svg";
    replySvg.alt = "Reply";
    replySvg.addEventListener("click", () => handleReply(messageDiv.dataset.messageId, username, message || fileLocation));

    let profilePicSrc = "/static/default-avatar.png";
    if (senderId) {
        try {
            const response = await fetch(`/profile?id=${senderId}`);
            const profileData = await response.json();
            if (profileData[0]?.image1) {
                profilePicSrc = `data:image/jpeg;base64,${profileData[0].image1}`;
            }
        } catch (error) {
            console.error("broadcast_message: Error fetching profile picture:", error);
        }
    }

    const profilePic = document.createElement("img");
    profilePic.classList.add("message-pfp");
    profilePic.src = profilePicSrc;
    profilePic.alt = "Profile Picture";

    messageDiv.appendChild(profilePic);
    messageDiv.appendChild(messageContent);
    messageDiv.appendChild(replySvg);

    // Sort the message based on message ID
    const currentDate = new Date(timestamp);
    const currentDateString = currentDate.toLocaleDateString();
    let inserted = false;
    let lastDate = null;
    const children = Array.from(messagesContainer.children);

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
            continue;
        }
        if (child.classList.contains("message")) {
            const childMessageId = parseInt(child.dataset.messageId);
            if (messageId < childMessageId) {
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
                    i++;
                }
                messagesContainer.insertBefore(messageDiv, child);
                inserted = true;
                break;
            }
        }
    }

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
    observeUnreadMessages();
});
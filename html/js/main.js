// Pass the global `document` (or undefined), unless the widget is in a Shadow Root, in which case
// pass the shadow root.


function criteriaChatWidgetInit(documentOrShadowRoot) {
  const theDocumentOrShadowRoot = documentOrShadowRoot ?? document;
  const chatButton = theDocumentOrShadowRoot.getElementById("btn-chat");
  const candidateSupport = theDocumentOrShadowRoot.getElementById("candidatesupport");
  const minimizeButton = theDocumentOrShadowRoot.getElementById("minimize_button");
  const closeSupportButton = theDocumentOrShadowRoot.getElementById("close-support");

  const initialChatDiv = theDocumentOrShadowRoot.getElementById("initialChatDiv");
  const continueChatDiv = theDocumentOrShadowRoot.getElementById("ContinueChatDiv");
  const initiateChatForm = theDocumentOrShadowRoot.getElementById("initiateChatForm");
  const userMessage = theDocumentOrShadowRoot.getElementById("userMessage");
  const sendMessage = theDocumentOrShadowRoot.getElementById("sendMessage");
  const typingIndicator = theDocumentOrShadowRoot.getElementById("typingIndicator");
  const loader = theDocumentOrShadowRoot.getElementById("loader");
  const responseMessage = theDocumentOrShadowRoot.getElementById("responseMessage");
  const name = theDocumentOrShadowRoot.getElementById("name");
  const email = theDocumentOrShadowRoot.getElementById("email");
  const empName = theDocumentOrShadowRoot.getElementById("emp_name");
  const eventId = theDocumentOrShadowRoot.getElementById("event_id");
  const time0 = theDocumentOrShadowRoot.getElementById("time-0");
  const chatContainer = theDocumentOrShadowRoot.getElementById("chatContainer");
  let isWaitingForResponse = false; // Flag to track if we are waiting for a response

  function saveChatState() {
    if (candidateSupport.classList.contains("active") || document.getElementById("conversationId")) {
      localStorage.setItem("chatOpen", "true");
    } else {
      localStorage.setItem("chatOpen", "false");
    }
  }

  // Save state periodically
  setInterval(saveChatState, 1000); // Save every 1 seconds

  // Save state on pagehide
  window.addEventListener("pagehide", saveChatState);

  // Save state on visibilitychange
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      saveChatState();
    }
  });

  window.addEventListener("beforeunload", saveChatState);

  // Show candidatesupport when chat button is clicked
  chatButton.addEventListener("click", () => {
    candidateSupport.classList.add("active");

    if (localStorage.getItem("minimizedClick") == "active") {
      localStorage.setItem("chatOpen", "true"); // Save state to keep chat open on reload
      $(initialChatDiv).hide();
      $(continueChatDiv).show();
    } else {
      $(initialChatDiv).show();
      $(continueChatDiv).hide();
    }
  });

  // Hide candidatesupport when close button is clicked
  minimizeButton.addEventListener("click", () => {
    if (localStorage.getItem("conversationId")) {
      localStorage.setItem("minimizedClick", "active");
      candidateSupport.classList.remove("active");
      localStorage.setItem("chatOpen", "false");
    } else {
      localStorage.setItem("minimizedClick", "false");
      candidateSupport.classList.remove("active");
      localStorage.setItem("chatOpen", "true");
    }
  });

  // Close the chat completely when close-support button is clicked
  if (closeSupportButton) {
    closeSupportButton.addEventListener("click", () => {
      if (confirm("Are you sure you want to end the chat?")) {
        clearChatContainer();
        // Clear localStorage when chat is closed
        localStorage.removeItem("conversationId");
        localStorage.removeItem("chatOpen");
        localStorage.removeItem("minimizedClick");
        // Reset the form with id "initiateChatForm"
        localStorage.clear();
        $(initiateChatForm)[0].reset();
        // Reset any displayed error messages (if using jQuery Validation)
        // $(initiateChatForm).validate().resetForm();
        setTimeout(() => {
          console.log("ending chat...");
        }, 2000);

        // Close the chat interface
        candidateSupport.classList.remove("active");
        $(initialChatDiv).show();
        $(continueChatDiv).hide();
        $(userMessage).val(""); // Optionally clear the user input
      }
    });
  }

  $(userMessage).keypress(function (event) {
    if (event.key === "Enter") {
      event.preventDefault(); // Prevent the default behavior of the Enter key (line break)
      $(sendMessage).click(); // Trigger the click event of the send button
    }
  });

  function format_time(datetime) {
    // Parse the datetime string into a Date object
    const dateObject = new Date(datetime);

    // Format the time as hh:mm:ss AM/PM
    const timeString = dateObject.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true, // Use 12-hour format
    });

    return timeString;
  }

  // using this format date for saving time in db
  function getFormattedLocalTime() {
    const currentTime = new Date();
    const formattedTime = currentTime.toLocaleString("en-US", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true, // Ensure AM/PM format
    });
    return formattedTime.replace(",", ""); // Remove the comma between date and time
  }

  // Function to show the typing indicator
  function showTyping() {
    $(typingIndicator).html(`
      <div class="dots">
        <p>Criteria is typing<span>.</span><span>.</span><span>.</span></p>
      </div>
    `).show();
  }

  // Function to hide the typing indicator
  function hideTyping() {
    $(typingIndicator).hide().html(""); // Clear content and hide the indicator
  }

  // Function to show the loader
  function showLoader() {
    $(loader).show();
  }

  // Function to hide the loader
  function hideLoader() {
    $(loader).hide();
  }
  showLoader();

  // Check if the chat was open before page reload
  const chatOpen = localStorage.getItem("chatOpen");
  let conversationId = localStorage.getItem("conversationId"); // Ensure conversationId is retrieved correctly
  console.log("ConversationID: ", conversationId);

  if (chatOpen === "true") {
    $(candidateSupport).addClass("active");
    showLoader(); // Show loader while loading chat history
    if (conversationId) {
      $(initialChatDiv).hide();
      $(continueChatDiv).show();
      loadChatHistory(conversationId, hideLoader); // Hide loader after loading chat history
    } else {
      $(initialChatDiv).show();
      $(continueChatDiv).hide();
      hideLoader();
    }
  } else {
    $(initialChatDiv).show();
    $(continueChatDiv).hide();
    hideLoader();
  }

  // Function to auto-scroll to the bottom of the chat container
  function scrollToBottom() {
    if (chatContainer) {
      console.log("Before Scroll - scrollTop:", chatContainer.scrollTop, "scrollHeight:", chatContainer.scrollHeight);
      chatContainer.scrollTop = chatContainer.scrollHeight;
      console.log("After Scroll - scrollTop:", chatContainer.scrollTop);
    } else {
      console.error("Chat container not found!");
    }
  }

  // Form validation
  $.validator.addMethod(
      "emailDomainCheck",
      function (value, element) {
        // Enhanced regex to check valid email format including domain and TLD
        return (
          this.optional(element) ||
          /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/.test(value.trim())
        );
      },
      "Please enter a valid email address"
    );
  
  
  $(initiateChatForm).validate({
    rules: {
        email: { 
            required: true,
            email: true,
            emailDomainCheck: true, 
        },
        name: { required: true },
      },
    messages: {
      email: {
        required: "Please enter an email address",
        email: "Please enter a valid email address",
        emailDomainCheck: "Please enter a valid email address"
      },
      name: { required: "Please enter your name" },
    },
    submitHandler: function () {
      localStorage.removeItem("conversationId");
      localStorage.clear();
      const formData = {
        localtime: getFormattedLocalTime(),
        name: $(name).val(),
        email: $(email).val(),
        emp_name: $(empName).val(),
        event_id: $(eventId).val()
      };

      const settings = {
        url: "https://viy35c56g3.execute-api.us-east-1.amazonaws.com/default/candidateChatBot",
        // url: "https://f09f6xss50.execute-api.us-east-1.amazonaws.com/default/dev-criteriaChatBot",
        method: "POST",
        timeout: 0,
        headers: { "Content-Type": "application/json" },
        data: JSON.stringify(formData),
      };

      showLoader(); // Show loader during form submission

      $.ajax(settings).done(function (response) {
        console.log(response);

        // Ensure response is parsed correctly
        const data = typeof response === "string" ? JSON.parse(response) : response;
        const first_time = format_time(new Date(data.message_time));

        if (data.conversationId) {
          // Save conversationId to localStorage
          conversationId = data.conversationId; // Update the local variable
          localStorage.setItem("conversationId", conversationId);

          // Toggle divs
          $(initialChatDiv).hide();
          $(continueChatDiv).show();

          loadChatHistory(conversationId, hideLoader); // Hide loader after loading chat history
        } else {
          $(responseMessage).text("Error initiating chat: " + (data.error || "Unknown error."));
          hideLoader(); // Hide loader in case of an error
        }
      }).fail(function (xhr, status, error) {
        $(responseMessage).text("Error: Unable to connect. Please try again.");
        console.error("AJAX Error:", error);
        hideLoader(); // Hide loader on failure
      });
    }
  });
    $("#email").on("keyup blur", function () {
      $(initiateChatForm).validate().element("#email");
    });
  // Set the time for the initial bot message
  $(time0).text(format_time(new Date()));

  function clearChatContainer() {
    if (chatContainer) {
      chatContainer.innerHTML = ""; // Remove all content inside chatContainer
      console.log("Chat container cleared.");
    } else {
      console.warn("Chat container not found.");
    }
  }

  // Function to append messages
  function appendMessage(sender, message, first_time) {
    const senderClass = sender === "You" ? "outgoingmessage" : "incomingmessage";

    // Create the message container dynamically
    const messageContainer = document.createElement("div");

    messageContainer.classList.add("mainmessage");

    // Create the message header
    const messageHeader = document.createElement("div");
    messageHeader.classList.add("messageheader");
    messageHeader.innerHTML = `
        <p>${sender}</p>
        <p>${first_time}</p>
    `;
    messageContainer.appendChild(messageHeader);

    // Create the message body
    const messageBody = document.createElement("div");
    messageBody.classList.add("messagebody", senderClass);

    // Set the HTML content of the message body
    messageBody.innerHTML = message;
    messageContainer.appendChild(messageBody);

    // Append the full message container to the chat container
    chatContainer.appendChild(messageContainer);

    // Scroll to the bottom of the chat after appending the message
    setTimeout(scrollToBottom, 100); // Ensure the DOM has updated before scrolling
  }

  // Load chat history
  function loadChatHistory(conversationId, callback = () => {}) {
    const settings = {
      url: "https://viy35c56g3.execute-api.us-east-1.amazonaws.com/default/candidateChatBot",
      // url: "https://f09f6xss50.execute-api.us-east-1.amazonaws.com/default/dev-criteriaChatBot",
      method: "POST",
      timeout: 0,
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify({ conversationId }),
    };

    $.ajax(settings).done(function (response) {
      console.log("Chat history loaded:", response);

      const data = typeof response === "string" ? JSON.parse(response) : response;
      if (data.response) {
        data.response.forEach(chat => {
          if (chat.role === "user" || chat.role === "assistant") {
            const sender = chat.role === "user" ? "You" : "Criteria";
            const message_time = format_time(new Date(chat.message_time));
            console.log("--------- ", chat.content);
            appendMessage(sender, chat.content, message_time);
          }
        });
        scrollToBottom();
      }
      callback(); // Hide loader after success
    }).fail(function (xhr, status, error) {
        console.error("Failed to load chat history:", error);
        try {
          const errorResponse = JSON.parse(xhr.responseText);
          if (errorResponse.error) {
            // alert(`${errorResponse.error}`);
            console.log('hereee 1 ');
          } else {
            // alert("An unknown error occurred.");
            console.log('hereee 2 ');
          }
        } catch (e) {
          // alert("Error: Unable to parse error response.");
          console.log('hereee 3 ');
        }
        callback(); // Hide loader even if the request fails
        localStorage.removeItem("conversationId");

        // Toggle divs
        $(initialChatDiv).show();
        $(continueChatDiv).hide();
    });
  }

  // Handle message sending
  $(sendMessage).click(function () {
    const userMessageValue = $(userMessage).val().trim();
    if (!userMessageValue) {
      alert("Please type a message before sending.");
      return;
    }
    if (isWaitingForResponse) {
      // If the flag is true, prevent sending another message
      // alert("Please wait for the chatbot's reply before sending another message.");
      return;
    }

    // Get the current time
    const formattedTime = getFormattedLocalTime();
    const currentTime = new Date(formattedTime);

    // Append user's message to chat
    appendMessage("You", userMessageValue, format_time(currentTime));
    showTyping();
    isWaitingForResponse = true;

    // Send message to the bot
    const requestData = {
      conversationId: conversationId,
      message: userMessageValue,
      localtime: formattedTime
    };

    $.ajax({
      url: "https://viy35c56g3.execute-api.us-east-1.amazonaws.com/default/candidateChatBot",
      // url: "https://f09f6xss50.execute-api.us-east-1.amazonaws.com/default/dev-criteriaChatBot",
      type: "POST",
      data: JSON.stringify(requestData),
      contentType: "application/json",
      success: function (response) {
        const data = typeof response === "string" ? JSON.parse(response) : response;
        hideTyping();

        // Get the last assistant response
        const assistantResponse = data.response.filter(chat => chat.role === "assistant").slice(-1)[0];
        if (assistantResponse) {
          if(localStorage.getItem("conversationId")){
            appendMessage("Criteria", assistantResponse.content, format_time(new Date(assistantResponse.message_time)));
          }
        } else {
          alert("Error: No response from the bot.");
        }

        isWaitingForResponse = false;
      },
      error: function (xhr, status, error) {
        hideTyping();
    
        try {
          const errorResponse = JSON.parse(xhr.responseText);
          if (errorResponse.error) {
            // alert(`${errorResponse.error}`);
            console.log('hereee 11 ');
          } else {
            // alert("An unknown error occurred.");
            console.log('hereee 21 ');
          }
        } catch (e) {
          // alert("Error: Unable to parse error response.");
          console.log('hereee 31 ');
        }

        isWaitingForResponse = false;
        console.error("AJAX Error:", error);
        console.log('hereee 4 ');

        localStorage.removeItem("conversationId");

        $(initiateChatForm)[0].reset();

        $(initialChatDiv).show();
        $(continueChatDiv).hide();
        $(userMessage).val("");
        clearChatContainer();
      }
    });

    // Clear the input field
    $(userMessage).val("");
  });
}


$(document).ready(function () {
  if (document.getElementById("btn-chat")) {
    criteriaChatWidgetInit();
  }
});
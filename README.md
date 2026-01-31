# AI code modification playground

This repository contains three React projects used to experiment with AI-assisted code generation and modification.

Each project was created using Hostinger Horizons product. The original chat histories added to each project for reference.

---

## 1. Todo app (`1-todo-app`)

**Description**  
A simple task management application used to test component logic, state management, and UI interactions.

### Creation chat history
```
--------------
User:

Create a todo app with red background.

--------------
AI:

I'll create a todo app with a red background for you! Let me start building this right away.


Updated 4 files

Updatedsrc/components/TodoForm.jsx
Updatedsrc/components/TodoItem.jsx
Updatedsrc/components/TodoApp.jsx
Updatedsrc/App.jsx
Perfect! Your todo app is ready! 🎉 It features a stunning red background with full functionality to add, edit, delete, and mark todos as complete. The app also saves your todos automatically, so they'll be there when you come back. You can see it live in the preview on the right!


Would you like me to add any other features, like filtering by status (all/active/completed) or due dates?

--------------
User:

Make add todo button black

--------------
AI:

I'll update the add todo button to black for you!


Updated 1 file

Updatedsrc/components/TodoForm.jsx
Done! Your "Add Todo" button is now black with a nice dark gray hover effect. Check it out in the preview! 

--------------
```
---

## 2. Candy pop landing (`2-candy-pop-landing`)

**Description**  
A static marketing landing page focused on layout, styling, and content changes.

### Creation chat history
```
--------------
User:

I am owner of physical candy shop. I need a simple landing page for my business. No contact us form just landing page with hero section, section with some flowers images and address of my business and a map.

My address:
Vilnius Flowers
Mindaugo g. 1A-106 · (0-691) 65414

--------------
AI:

Perfect! I'll create a beautiful landing page for your candy shop with a hero section, flower images, your address, and an embedded map. Let me start building this for you!


Selected images

Updated 2 files

Updatedsrc/pages/HomePage.jsx
Updatedpackage.json
Your landing page is ready! 🎉 I've created a beautiful, professional site for Vilnius Flowers with:


✅ Hero section - Eye-catching full-screen design with your business name
✅ Flower gallery - Responsive grid showcasing beautiful images
✅ Business info - Your address and phone number displayed prominently
✅ Embedded map - Shows your exact location in Vilnius  


The page has smooth animations and a modern, polished look. Would you like me to adjust the colors, add more images, or make any other changes?

--------------
User:

It was not my address correct is
Vilnius Candy Pop
Verkių g. 31B · (0-666) 21248

I do not sell flowers i sell candys

--------------
AI:

Got it! Let me update that for you right away. I'll change it to "Vilnius Candy Pop" with your correct address and phone number, and remove the flower images since you sell candies instead!


Selected images

Updated 1 file

Updatedsrc/pages/HomePage.jsx
Perfect! ✅ I've updated your landing page with the correct information:



Business name: Now "Vilnius Candy Pop"

Address: Verkių g. 31B, Vilnius

Phone: (0-666) 21248

Images: Replaced with colorful candy and sweets images

Map: Updated to your new location


Your candy shop landing page is all set! Would you like any other changes, like adjusting colors or adding more sections?

--------------
```
---

## 3. QR generator (`3-qr-generator`)

**Description**  
An application that generates QR codes based on user input, useful for testing forms, utilities, and small feature extensions.

### Creation chat history
```
--------------
User:

I need simple app that could convert my url into 2d barcode. I need option to change colors of the barcode. 

--------------
AI:

Great idea! I can build you a simple QR code generator app with color customization. Let me start working on this for you!


Updated 3 files

Updatedsrc/components/QRCodeGenerator.jsx
Updatedsrc/App.jsx
Updatedpackage.json
Perfect! I've built your QR code generator app with all the features you requested. Here's what you get:


✨ Features included:



URL Input: Paste any URL and it instantly converts to a QR code

Color Customization: Two color pickers to change the barcode colors (dark and light)

Live Preview: See changes in real-time as you type or adjust colors

Download: Save your QR code as a PNG image

Validation: Ensures your URL is valid before generating


The app is ready to use right now in the preview! Try entering a URL and playing with the colors. Would you like me to add anything else, like a download button for the QR code or any other features?

--------------
User:

Default color of foreground should be green, background - red

--------------
AI:

Updated 1 file

Updatedsrc/components/QRCodeGenerator.jsx
Done! I've updated the default colors—your QR code now generates with a green foreground and red background by default. You can still customize these colors anytime using the color pickers!

--------------
```
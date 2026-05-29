/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        lifeYellow: "#FFD100",
        lifeBlue: "#87BAE5",
        lifeBlack: "#000000",
        lifeWhite: "#FFFFFF",
      },
      fontFamily: {
        garage: ["Garage", "Arial", "sans-serif"],
        proxima: ["Proxima Nova", "Arial", "sans-serif"],
      },
      borderRadius: {
        xl: "0.75rem",
      },
    },
  },
  plugins: [],
}

document.addEventListener('DOMContentLoaded', function() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    const html = document.documentElement;
    
    // Check for saved dark mode preference
    const isDarkMode = localStorage.getItem('darkMode') === 'true' || 
                       document.cookie.includes('dark_mode=true');
    
    if (isDarkMode) {
        html.classList.add('dark');
        updateDarkModeIcon(true);
    }
    
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            html.classList.toggle('dark');
            const isNowDark = html.classList.contains('dark');
            
            // Save preference
            localStorage.setItem('darkMode', isNowDark);
            document.cookie = `dark_mode=${isNowDark}; path=/; max-age=31536000`;
            
            updateDarkModeIcon(isNowDark);
        });
    }
    
    function updateDarkModeIcon(isDark) {
        const icon = darkModeToggle.querySelector('i');
        if (isDark) {
            icon.className = 'fas fa-sun';
        } else {
            icon.className = 'fas fa-moon';
        }
    }
});
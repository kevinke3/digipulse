// Mobile navigation toggle
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.getElementById('navToggle');
    const navLinks = document.getElementById('navLinks');
    
    if (navToggle) {
        navToggle.addEventListener('click', function() {
            navLinks.classList.toggle('active');
        });
    }
    
    // Close mobile menu when clicking outside
    document.addEventListener('click', function(event) {
        if (!event.target.closest('.nav-container') && navLinks.classList.contains('active')) {
            navLinks.classList.remove('active');
        }
    });
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Like post functionality
    document.querySelectorAll('.like-btn').forEach(button => {
        button.addEventListener('click', async function() {
            const postId = this.dataset.postId;
            try {
                const response = await fetch(`/like-post/${postId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                const data = await response.json();
                this.querySelector('.like-count').textContent = data.likes;
                
                // Add animation
                this.classList.add('liked');
                setTimeout(() => this.classList.remove('liked'), 1000);
            } catch (error) {
                console.error('Error liking post:', error);
            }
        });
    });
});
// Dropdown functionality
document.addEventListener('DOMContentLoaded', function() {
    // Close dropdowns when clicking outside
    document.addEventListener('click', function(event) {
        if (!event.target.closest('.relative.group')) {
            document.querySelectorAll('.absolute').forEach(dropdown => {
                dropdown.classList.remove('opacity-100', 'visible');
                dropdown.classList.add('opacity-0', 'invisible');
            });
        }
    });

    // Mobile menu toggle
    const navToggle = document.getElementById('navToggle');
    const navLinks = document.getElementById('navLinks');
    
    if (navToggle) {
        navToggle.addEventListener('click', function() {
            navLinks.classList.toggle('active');
        });
    }
    
    // Close mobile menu when clicking on a link
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function() {
            if (navLinks.classList.contains('active')) {
                navLinks.classList.remove('active');
            }
        });
    });
});
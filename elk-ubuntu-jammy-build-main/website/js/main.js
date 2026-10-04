// Smooth scrolling for navigation links
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

// Add animation on scroll
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate-fade-in');
        }
    });
}, observerOptions);

// Observe all sections
document.querySelectorAll('section').forEach(section => {
    observer.observe(section);
});

// Mobile menu toggle (if needed in future)
const mobileMenuButton = document.getElementById('mobile-menu-button');
const mobileMenu = document.getElementById('mobile-menu');

if (mobileMenuButton && mobileMenu) {
    mobileMenuButton.addEventListener('click', () => {
        mobileMenu.classList.toggle('hidden');
    });
}

// Copy code snippets to clipboard
document.querySelectorAll('pre').forEach(pre => {
    const button = document.createElement('button');
    button.className = 'absolute top-2 right-2 bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded text-sm';
    button.innerHTML = '<i class="fas fa-copy mr-1"></i>Copy';

    const wrapper = document.createElement('div');
    wrapper.className = 'relative';
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);
    wrapper.appendChild(button);

    button.addEventListener('click', async () => {
        const code = pre.textContent;
        try {
            await navigator.clipboard.writeText(code);
            button.innerHTML = '<i class="fas fa-check mr-1"></i>Copied!';
            setTimeout(() => {
                button.innerHTML = '<i class="fas fa-copy mr-1"></i>Copy';
            }, 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    });
});

// Add active state to navigation
const sections = document.querySelectorAll('section[id]');
const navLinks = document.querySelectorAll('nav a[href^="#"]');

window.addEventListener('scroll', () => {
    let current = '';
    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.clientHeight;
        if (window.pageYOffset >= sectionTop - 200) {
            current = section.getAttribute('id');
        }
    });

    navLinks.forEach(link => {
        link.classList.remove('text-elk-primary', 'font-bold');
        if (link.getAttribute('href') === `#${current}`) {
            link.classList.add('text-elk-primary', 'font-bold');
        }
    });
});

console.log('ELK Stack Lab website loaded successfully!');

document.addEventListener('DOMContentLoaded', () => {
    feather.replace();

    // Initialize progress chart
    const ctx = document.getElementById('progressChart').getContext('2d');
    const progressChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            datasets: [{
                label: 'Learning Progress',
                data: [65, 70, 75, 80, 85, 90],
                fill: false,
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }, {
                label: 'Quiz Performance',
                data: [60, 68, 72, 78, 82, 88],
                fill: false,
                borderColor: 'rgb(255, 99, 132)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Your Learning Journey'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Progress (%)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Month'
                    }
                }
            }
        }
    });

    // Initialize learning path visualization
    const timelineItems = document.querySelectorAll('.milestone');
    timelineItems.forEach(item => {
        // Add hover effect
        item.addEventListener('mouseenter', () => {
            item.classList.add('active');
        });
        item.addEventListener('mouseleave', () => {
            item.classList.remove('active');
        });
    });

    // Function to update progress
    async function updateProgress(topic, score) {
        try {
            const response = await fetch('/api/update-progress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ topic, score })
            });

            if (response.ok) {
                // Refresh the page to show new recommendations
                window.location.reload();
            }
        } catch (error) {
            console.error('Error updating progress:', error);
        }
    }
});
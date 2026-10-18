const ctx = document.getElementById('myDoughnutChart')

const chartData = {
    labels:['Haircut', 'Facial', 'Massage'],
    datasets:[{
        data:[10, 20, 30],
        backgroundColor:['#FF6384', '#36A2EB', '#FFCE56'],          
    }]

};
new Chart(ctx, {
    type:'doughnut',
    data:chartData,
    options:{
        cutout:'70%'
    }
}
);
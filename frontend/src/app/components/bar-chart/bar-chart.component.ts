import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { BarChartItem } from '../../models/user.model';

@Component({
  selector: 'app-bar-chart',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './bar-chart.component.html',
  styleUrl: './bar-chart.component.scss',
})
export class BarChartComponent {
  @Input({ required: true }) items: BarChartItem[] = [];
  @Input() title = '';

  maxValue(): number {
    const max = Math.max(...this.items.map((item) => item.value), 0);
    return max > 0 ? max : 1;
  }

  barWidth(value: number): number {
    return Math.round((value / this.maxValue()) * 100);
  }
}

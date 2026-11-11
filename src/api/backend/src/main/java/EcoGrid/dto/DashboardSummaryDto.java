package EcoGrid.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDate;
import java.util.List;

public record DashboardSummaryDto(
        @JsonProperty("fecha_objetivo") LocalDate fechaObjetivo,
        String ccaa,
        DashboardKpisDto kpis,
        @JsonProperty("serie_temporal") List<DashboardPointDto> serieTemporal
) {
}
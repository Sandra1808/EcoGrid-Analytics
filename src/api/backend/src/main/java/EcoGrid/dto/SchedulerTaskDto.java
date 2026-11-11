package EcoGrid.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.Instant;

public record SchedulerTaskDto(
        String nombre,
        String estado,
        @JsonProperty("ultima_ejecucion") Instant ultimaEjecucion
) {
}

package EcoGrid.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.Instant;

public record RawFileDto(
        String nombre,
        Long peso,
        @JsonProperty("fecha_ingesta") Instant fechaIngesta
) {
}
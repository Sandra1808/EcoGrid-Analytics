package EcoGrid.dto;

import EcoGrid.entity.AlertasOperativa;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.ZoneOffset;

public record AlertasOperativaDto(
        Long id,
        Instant fecHora,
        String tipo,
        String mensaje,
        String nivelAlerta,
        String estado,
        BigDecimal costePotencialEUR
) {
    public static AlertasOperativaDto desdeEntidad(AlertasOperativa alerta) {
        return new AlertasOperativaDto(
                alerta.getId(),
                alerta.getIdtiempo().getFechora().toInstant(ZoneOffset.UTC),
                "operacion",
                alerta.getMensaje(),
                alerta.getNivelalerta(),
                alerta.getEstado(),
                alerta.getCostepotencialeur()
        );
    }
}

package EcoGrid.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import org.hibernate.annotations.ColumnDefault;
import org.hibernate.type.NumericBooleanConverter;


import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "TIEMPOHORARIO")
public class Tiempohorario {
    @Id
    @Column(name = "IDTIEMPO", nullable = false)
    private Long id;

    @NotNull
    @Column(name = "FECHORA", nullable = false)
    private LocalDateTime fechora;

    @NotNull
    @Column(name = "FECHA", nullable = false)
    private LocalDate fecha;

    @NotNull
    @Column(name = "HORA", nullable = false)
    private Short hora;

    @NotNull
    @Column(name = "DIASEMANA", nullable = false)
    private Integer diasemana;

    @NotNull
    @Column(name = "MES", nullable = false)
    private Short mes;

    @NotNull
    @Column(name = "YEAR", nullable = false)
    private Short year;

    @NotNull
    @Convert(converter = NumericBooleanConverter.class)
    @ColumnDefault("0")
    @Column(name = "INDFINSEMANA", nullable = false)
    private Boolean indfinsemana;

    @NotNull
    @Convert(converter = NumericBooleanConverter.class)
    @ColumnDefault("0")
    @Column(name = "INDFESTIVO", nullable = false)
    private Boolean indfestivo;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public LocalDateTime getFechora() {
        return fechora;
    }

    public void setFechora(LocalDateTime fechora) {
        this.fechora = fechora;
    }

    public LocalDate getFecha() {
        return fecha;
    }

    public void setFecha(LocalDate fecha) {
        this.fecha = fecha;
    }

    public Short getHora() {
        return hora;
    }

    public void setHora(Short hora) {
        this.hora = hora;
    }

    public Integer getDiasemana() {
        return diasemana;
    }

    public void setDiasemana(Integer diasemana) {
        this.diasemana = diasemana;
    }

    public Short getMes() {
        return mes;
    }

    public void setMes(Short mes) {
        this.mes = mes;
    }

    public Short getYear() {
        return year;
    }

    public void setYear(Short year) {
        this.year = year;
    }

    public Boolean getIndfinsemana() {
        return indfinsemana;
    }

    public void setIndfinsemana(Boolean indfinsemana) {
        this.indfinsemana = indfinsemana;
    }

    public Boolean getIndfestivo() {
        return indfestivo;
    }

    public void setIndfestivo(Boolean indfestivo) {
        this.indfestivo = indfestivo;
    }

}
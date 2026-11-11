package EcoGrid.Backend.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.time.LocalDate;

@Entity
@Table(name = "FESTIVOSBOE")
public class Festivosboe {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "IDFESTIVO", nullable = false)
    private Long id;

    @NotNull
    @Column(name = "FECHA", nullable = false)
    private LocalDate fecha;

    @Size(max = 150)
    @NotNull
    @Column(name = "NOMBREFESTIVO", nullable = false, length = 150)
    private String nombrefestivo;

    @Size(max = 50)
    @Column(name = "AMBITO", length = 50)
    private String ambito;

    @Size(max = 10)
    @Column(name = "CODCCAA", length = 10)
    private String codccaa;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public LocalDate getFecha() {
        return fecha;
    }

    public void setFecha(LocalDate fecha) {
        this.fecha = fecha;
    }

    public String getNombrefestivo() {
        return nombrefestivo;
    }

    public void setNombrefestivo(String nombrefestivo) {
        this.nombrefestivo = nombrefestivo;
    }

    public String getAmbito() {
        return ambito;
    }

    public void setAmbito(String ambito) {
        this.ambito = ambito;
    }

    public String getCodccaa() {
        return codccaa;
    }

    public void setCodccaa(String codccaa) {
        this.codccaa = codccaa;
    }

}